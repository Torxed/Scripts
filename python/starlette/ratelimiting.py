# A Middleware for rate limiting using datetime.timedelta() definitions

import re
import datetime

class RateLimiter:
	"""
	rate limit middleware
	"""

	def __init__(self, app, config, *args, **kwargs) -> None:
		self.app = app
		self.config = {
			re.compile(path): value for path, value in config.items()
		}
		self.db = {}

	async def dispatch(self, request, call_next):
		response = await call_next(request)
		# response.headers['Custom'] = 'Example'
		return response

	async def __call__(self, scope, receive, send):
		# print(scope, receive, send)
		if scope["type"] != "http":
			# print(f"Odd scope {scope['type']}")
			return await self.app(scope, receive, send)

		url = scope["path"]
		if not (client := scope['client']):
			for header in scope['headers']:
				if header[0] == b'x-real-ip':
					client = header[1].decode('UTF-8')
					break
				elif header[0] == b'x-forwarded-for':
					client = header[1].decode('UTF-8')
					break

		# We have no way of knowing who accessed this resource
		if not client or client not in self.db:
			if client:
				self.db[client] = {
					'urls' : {
						url : {
							datetime.datetime.now() : True
						}
					}
				}
			# print("User is a new user, not rate limited")
			return await self.app(scope, receive, send)

		for pattern, endpoint_config in self.config.items():
			if not pattern.match(url):
				continue

			# print(f"Matched pattern: {pattern} with conf {endpoint_config}")
			if not url in self.db[client]['urls']:
				self.db[client]['urls'][url] = {}

			self.db[client]['urls'][url][datetime.datetime.now()] = True
			
			if len(self.db[client]['urls'][url]) < endpoint_config['hits']:
				# print("User is not rate limited")
				return await self.app(scope, receive, send)
			else:
				# Clean all older visits
				for visit in list(self.db[client]['urls'][url].keys()):
					if datetime.datetime.now() - visit > endpoint_config['window']:
						del(self.db[client]['urls'][url][visit])

				# Check again after cleaning
				if len(self.db[client]['urls'][url]) < endpoint_config['hits']:
					# print("User is not rate limited any longer")
					return await self.app(scope, receive, send)

				else:
					# Blocked
					print(f"User {client} is rate limited on {url} ({len(self.db[client]['urls'][url])} hits within {endpoint_config['window']})")
					await send(
						{
							"type": "http.response.start",
							"status": 429,
							"headers": [
								(b"retry-after", str(5).encode("ascii")),
							],
						}
					)
					return await send({"type": "http.response.body", "body": b"", "more_body": False})

		# No URL matched:
		return await self.app(scope, receive, send)
