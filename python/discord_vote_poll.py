import discord

import aiohttp, asyncio, json
import urllib.parse
import urllib.request

"""
Syntax for a poll:

!poll title
something
here
"""

DISCORD_TOKEN = 'A unique discord token'

bot_info = {
	'server_name' : 'BlackHat 2020',
	'_guild_obj' : None,
	'_members' : {},
	'_roles' : {},
	'_channels' : {}
}

emoji_index = {
	0 : '0\N{COMBINING ENCLOSING KEYCAP}',
	1 : '1\N{COMBINING ENCLOSING KEYCAP}',
	2 : '2\N{COMBINING ENCLOSING KEYCAP}',
	3 : '3\N{COMBINING ENCLOSING KEYCAP}',
	4 : '4\N{COMBINING ENCLOSING KEYCAP}',
	5 : '5\N{COMBINING ENCLOSING KEYCAP}',
	6 : '6\N{COMBINING ENCLOSING KEYCAP}',
	7 : '7\N{COMBINING ENCLOSING KEYCAP}',
	8 : '8\N{COMBINING ENCLOSING KEYCAP}',
	9 : '9\N{COMBINING ENCLOSING KEYCAP}',
	10 : '\U0001F52B',
	11 : '🏕️',
	12 : '🔥',
	13 : '🥎',
	14 : '🚓',
	15 : '🍺',
	16 : '🙈',
	17 : '💄',
	18 : '⛅',
	19 : '🙄',
	20 : '🎄'
}

class BlackHat(discord.Client):
	async def on_ready(self):
		print(f'{client.user} has connected.')
		# Cache the server (guild) handle, roles, members and channels.
		for guild in client.guilds:
			if guild.name == bot_info['server_name']:
				bot_info['_guild_obj'] = guild

				for member in guild.members:
					bot_info['_members'][member.id] = member

				for role in bot_info['_guild_obj'].roles:
					bot_info['_roles'][role.id] = role

				for channel in guild.channels:
					bot_info['_channels'][channel.name] = channel

	async def on_member_join(self, member):
		# Keep updating members.
		bot_info['_members'][member.id] = member

	async def talley_votes(self, reaction):
		channel = self.get_channel(reaction.channel_id)
		message = await channel.fetch_message(reaction.message_id)

		votes = {}

		for reaction in message.reactions:
			async for reactor in reaction.users():
				if not reaction.emoji in votes: votes[reaction.emoji] = 0

				votes[reaction.emoji] += 1

		leading_votes = {}
		all_votes = votes.values()
		highest_vote = max(all_votes)

		for emoji, vote in votes.items():
			if vote < highest_vote: continue
			leading_votes[emoji] = vote

		if not 'Current winning poll: ' in message.content:
			await message.edit(content=message.content + f'\nCurrent winning poll: {", ".join(leading_votes.keys())}')
		else:
			last_poll_result_pos = message.content.find('Current winning poll: ')-1 # Remove pre-pended \n
			message_content = message.content[:last_poll_result_pos]
			await message.edit(content=message_content + f'\nCurrent winning poll: {", ".join(leading_votes.keys())}')

	async def on_raw_reaction_remove(self, reaction, *args, **kwargs):
		await self.talley_votes(reaction)

	async def on_raw_reaction_add(self, reaction, *args, **kwargs):
		await self.talley_votes(reaction)

	async def on_message(self, message):
		# Check if we're sending to a server (guild) and not a direct message/private message
		if message.guild:
			
			# Check if the message starts with !poll
			if message.content[:5] == '!poll':

				# Check if the user has a role called 'Admin' (case sensitive)
				admin = False
				for role in message.author.roles:
					if role.name == 'Admin':
						admin = True
						break

				if admin:
					# Split out the title and individual poll items.
					cmd, title = message.content.split(' ', 1)
					title, *poll_items = title.split('\n')

					# Build the new message that the bot will send out:
					poll = f'New poll: {title}\n'
					emojis = []
					for index, item in enumerate(poll_items):
						poll += f'{emoji_index[index]}: {item}\n'
						emojis.append(emoji_index[index])

					# Send it, and then add the reactions/emoji's as "buttons" below
					sent_message = await bot_info['_channels']["polls"].send(poll)
					for emoji in emojis:
						await sent_message.add_reaction(emoji)

				await message.delete() # Delete the !poll message


client = BlackHat()
client.run(DISCORD_TOKEN)
