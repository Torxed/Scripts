import math

class Pos:
	def __init__(self, x, y):
		self.x = x
		self.y = y

	def __repr__(self):
		return f'Pos(x: {self.x}, y: {self.y})'

class Tangent:
	def __init__(self, delta):
		self.delta = delta

	def __repr__(self):
		return f'tan(rad: {self.radiance}, deg: {self.angle})'

	@property
	def radiance(self):
		return math.atan2(self.delta.y, self.delta.x)

	@property
	def angle(self):
		return (self.radiance * (180/math.pi) + 360) % 360

class Delta:
	def __init__(self, source, destination):
		self.source = source
		self.destination = destination

	def __repr__(self):
		return f'Δ(x: {self.x}, y: {self.y})'

	@property
	def x(self):
		return self.destination.x - self.source.x

	@property
	def y(self):
		return self.destination.y - self.source.y

	@property
	def distance(self):
		pass

class Vector:
	def __init__(self, source, angle):
		self.source = source
		self.angle = angle

	def __repr__(self):
		return f'Vector(source: {self.source}, angle: {this.angle})'

	def move(self, distance):
		x_multiplier = math.cos(((self.angle)/180)*math.pi)
		y_multiplier = math.sin(((self.angle)/180)*math.pi)

		return Pos(x=self.source.x + (x_multiplier * distance),
					y=self.source.y + (y_multiplier * distance))

class Distance(Delta):
	def __repr__(self):
		return f'Distance({self.pixels})'

	@property
	def pixels(self):
		return pow(pow(self.destination.x - self.source.x, 2) + pow(self.destination.y - self.source.y, 2), 0.5)

if __name__ == '__main__':
	start = Pos(50, 70)
	destination = Pos(120, 120)

	delta = Delta(start, destination)
	tangent = Tangent(delta)

	new_position = Vector(start, tangent.angle).move(distance=5)
	distance = Distance(start, new_position)

	print('Start: ' + str(start))
	print('Destination: ' + str(destination))
	print('Delta: ' + str(delta))
	print('Tangent: ' + str(tangent))
	print('Degrees: ' + str(int(tangent.angle)))
	print('New pos: ' + str(new_position))
	print('Distance in pixels: ' + str(distance))
