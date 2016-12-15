import pyglet, os, shutil, urllib
from pyglet.gl import *
from subprocess import check_output, Popen, PIPE, STDOUT
from os.path import isfile, isdir, expanduser
from threading import *
from time import time, sleep

# REQUIRES: AVBin
pyglet.options['audio'] = ('alsa', 'openal', 'silent')
application_category = {'chromium' : 'internet',
						'firefox' : 'internet',
						'skype' : 'internet',
						'pidgin' : 'internet',
						'thunderbird' : 'internet',
						'tint2' : None,}

# xfce4-notifyd 

"""
## Remove auto-login+startup added by the installer:
os.remove('/etc/systemd/system/getty@tty1.service.d/autologin.conf')
shutil.rmtree('/etc/systemd/system/getty@tty1.service.d')
with open(expanduser("~") + '/.config/openbox/autostart', 'rb') as fh:
	data = fh.read()
with open(expanduser("~") + '/.config/openbox/autostart', 'wb') as fh:
	for line in data:
		if line != 'python2 ~/first_boot.py &':
			fh.write(line)
"""

class run():
	def __init__(self, cmd):
		self.cmd = cmd
		self.stdout = None
		self.stdin = None
		self.x = None
		self.run()

	def run(self):
		self.x = Popen(self.cmd, shell=True, stdout=PIPE, stderr=STDOUT, stdin=PIPE)
		self.stdout, self.stdin = self.x.stdout, self.x.stdin

	def wait(self, text):
		i = 0
		while self.x.poll() == None:
			time.sleep(0.2)

		if self.poll() in (0, '0'):
			#self.output.beginning(' [OK] ')
			self.close()
			return True
		else:
			#self.output.beginning(' ![Error] ')
			print(str([self.cmd]))
			print(self.stdout.read())
			self.close()
			return False

	def write(self, what, enter=True):
		if enter:
			if len(what) <= 0 or not what[-1] == '\n':
				what += '\n'
		self.stdin.write(what)

	def poll(self):
		return self.x.poll()

	def getline(self):
		while True:
			try:
				line = self.stdout.readline()
			except:
				break
			if len(line) <= 0: break
			yield line

	def getlines(self):
		return self.stdout.readlines()

	def close(self):
		self.stdout.close()
		self.stdin.close()

def rebuild_OpenBoxMenu(category, menu_item, cmd=None):
	_file = expanduser("~") + '/.config/openbox/menu.xml'
	if isfile(_file):
		with open(_file, 'rb') as fh:
			rows = fh.read()
		if not menu_item.lower() in rows.lower():
			with open(_file, 'wb') as fh:
				for row in rows.split('\n'):
					fh.write(row+'\n')
					if 'label="' + category.lower() + '">' in row.lower():
						fh.write('<item label="' + menu_item + '">\n')
						fh.write('	<action name="Execute">\n')
						if not cmd:
							cmd = menu_item.lower()
						fh.write('		<execute>' + cmd + '</execute>\n')
						fh.write('	</action>\n')
						fh.write('</item>\n')
	else:
		return False
	return True

class Spr (pyglet.sprite.Sprite):
	def __init__(self, texture=None, width=None,x=None,y=None):
		if not texture: return texture
		self.texture = pyglet.image.load(texture)
		super(Spr, self).__init__(self.texture)
		if width:
			while self.width > width:
				self.scale -= 0.1
		self.opacity = 255
		if x:
			self.x = x
		if y:
			self.y = y

	def click(self, x, y):
		if x > self.x and x < (self.x + self.width):
			if y > self.y and y < (self.y + self.height):
				return True

	def move(self, x, y):
		self.x += x
		self.y += y

	def update(self):
		self.opacity += 10
		if self.opacity > 255:
			self.opacity = 255

	def _draw(self):
		self.draw()

class Select(Spr):
	def __init__(self, title='Test', msg='', options=None, installer=None, large=False, exlusive=False):
		if not options: return options

		if large:
			super(Select, self).__init__('MsgBox_large.png')
			self.x = 150
			self.y = 20
		else:
			super(Select, self).__init__('MsgBox.png')
			self.x = 250
			self.y = 113

		self.draws = {'1-msg' : pyglet.text.Label(msg, multiline=True, width=self.width-30, font_size=10, x=self.x+15, y=self.y+self.height-45),
					'2-title' : pyglet.text.Label(title, anchor_x='center', font_size=12, x=self.x+self.width/2, y=self.y+self.height-20),
					'3-accept' : Spr('./icons/accept.png', 32, self.x+self.width/2-16, self.y+15)}
		if large:
			self.draws['2-title'].y -= 5

		self.buttons = {}
		starterpos = self.x+self.width/len(options)-((64*len(options))/len(options))
		for option in options:
			if isfile('./icons/' + option + '.png'):
				self.buttons[option] = Spr('./icons/' + option + '.png', 64, starterpos, self.y+60)
				self.buttons[option].opacity = 100
				starterpos += 64
			else:
				print 'Missing file for option window: ' + option + '.png'

		self.Answer = None
		self.installer = installer
		self.exlusive = exlusive

	def replace(self, what, _with, width=64, x=None, y=None):
		if what in self.buttons:
			opacity = self.buttons[what].opacity
			if not x:
				x = self.buttons[what].x
			else:
				x += self.x
			if not y:
				y = self.buttons[what].y
			else:
				y += self.y
			self.buttons[what] = Spr('./icons/' + _with + '.png', width, x, y)
			self.buttons[what].opacity = opacity

	def add(self, title, obj, x, y):
		self.draws[title] = obj
		self.draws[title].x = self.x+x
		self.draws[title].y = self.y+y

	def move(self, x, y):
		self.x += x
		self.y += y

		for obj in self.draws:
			self.draws[obj].x += x
			self.draws[obj].y += y
		for obj in self.buttons:
			self.buttons[obj].x += x
			self.buttons[obj].y += y

	def click(self, x, y):
		if x > self.x and x < (self.x + self.width):
			if y > self.y and y < (self.y + self.height):
				
				if x > self.draws['3-accept'].x and x < (self.draws['3-accept'].x + self.draws['3-accept'].width):
					if y > self.draws['3-accept'].y and y < (self.draws['3-accept'].y + self.draws['3-accept'].height):
						self.Answer = True

				for button in self.buttons:
					b = self.buttons[button]
					if x > b.x and x < (b.x + b.width):
						if y > b.y and y < (b.y + b.height):
							self.buttons[button].opacity = 255
							if self.installer:
								self.installer.queue.append(button)
								if self.exlusive:
									self.Answer = button
							return button
				return True

	def _draw(self):
		self.draw()
		for obj in sorted(self.draws):
			self.draws[obj].draw()
		for obj in self.buttons:
			self.buttons[obj].draw()


class MsgBox(Spr):
	def __init__(self, title='Test', msg='This is a test\nWith numoures lines that should clip in the right place', Cancel=True, large=False):
		if large:
			super(MsgBox, self).__init__('MsgBox_large.png')
			self.x = 150
			self.y = 20
		else:
			super(MsgBox, self).__init__('MsgBox.png')
			self.x = 250
			self.y = 113

		self.Cancel = Cancel
		self.x = 250
		self.y = 113

		self.Answer = None
		
		self.title = pyglet.text.Label(title, anchor_x='center', font_size=12, x=self.x+self.width/2, y=self.y+self.height-20)
		self.msg = pyglet.text.Label(msg, multiline=True, width=self.width-30, font_size=10, x=self.x+15, y=self.y+self.height-45)
		self.accept = Spr('./icons/accept.png', 32, self.x+self.width/2-48, 125) #438

		self.draws = {'1-msg' : self.msg, '2-title' : self.title, '3-accept' : self.accept}
		if large:
			self.draws['2-title'].y -= 5

		if Cancel:
			self.cancel = Spr('./icons/cancel.png', 32, self.x+self.width/2+16, 125) #345
			self.draws['3-cancel'] = self.cancel
		else:
			self.draws['3-accept'].x = self.x+self.width/2-8 #392


	def add(self, title, obj, x, y):
		self.draws[title] = obj
		self.draws[title].x = self.x+x
		self.draws[title].y = self.y+y

	def move(self, x, y):
		self.x += x
		self.y += y

		for obj in self.draws:
			self.draws[obj].x += x
			self.draws[obj].y += y

	def click(self, x, y):
		if x > self.x and x < (self.x + self.width):
			if y > self.y and y < (self.y + self.height):
				
				if x > self.accept.x and x < (self.accept.x + self.accept.width):
					if y > self.accept.y and y < (self.accept.y + self.accept.height):
						self.Answer = True

				if self.Cancel:
					if x > self.cancel.x and x < (self.cancel.x + self.cancel.width):
						if y > self.cancel.y and y < (self.cancel.y + self.cancel.height):
							self.Answer = False

				return True

	def _draw(self):
		self.draw()
		for obj in sorted(self.draws):
			self.draws[obj].draw()

		#self.accept.draw()
		#if self.Cancel:
		#	self.cancel.draw()
		#self.msg.draw()
		#self.title.draw()

class pacman(Thread):
	def __init__(self, spritelist):
		Thread.__init__(self)
		self.sprites = spritelist
		self.queue = []
		self.added = []
		self.start()

	def run(self):
		for thread in enumerate():
			if thread.name == 'MainThread':
				main = thread
				break

		last = time()
		installing = None
		while main.is_alive():
			if time()-last > 1:
				for item in check_output('pacman -Q', shell=True).split('\n'):
					if len(item) <= 0: continue
					name, version = item.split(' ',1)
					if not name in self.added and isfile('./icons/' + name + '.png'):
						self.sprites[name] = './icons/' + name + '.png', 64
						self.added.append(name)
			if len(self.queue) > 0:
				print 'Installing ' + str(self.queue[0])
				"""
				if not installing or installing.poll() != None:
					if installing:
						installing.close()
						installing = None
						category = 'Accessories'
						if self.queue[0] in application_category:
							category = application_category[self.queue[0]]
						if category:
							rebuild_OpenBoxMenu(self.queue[0], self.queue[0])
					installing = run('echo | sudo pacman --noconfirm -S ' + self.queue.pop(0))
				elif installing:
					print installing.getline()
				"""
			sleep(0.02)

class main (pyglet.window.Window):
	def __init__ (self):
		super(main, self).__init__(800, 400, fullscreen = False)
		#urllib.urlretrieve("http://www.psdgraphics.com/wp-content/uploads/2012/02/blank-button-template.jpg", "button.jpg")
		self.bg = Spr('background.jpg')
		#self.chromium = 
		#self.MsgBox = None

		# 'chromium' : Spr('./icons/chromium.png', 64)
		self.sprites = {'MsgBox' : None}
		self.merge_sprites = {}

		self.PacMan = pacman(self.merge_sprites)

#		self.MsgBox.x, self.MsgBox.y = 250,113
		#packages = {}
		#for item in check_output('pacman -Q', shell=True).split('\n'):
		#	if len(item) <= 0: continue
		#	name, version = item.split(' ',1)
		#	if isfile('./icons/' + name + '.png'):
		#		packages[name] = version
		#		self.sprites[name] = Spr('./icons/' + name + '.png', 64)

		#self.sprites = [self.chromium, self.MsgBox]

		self.checks = {'SOUND' : None}
		self.checks['systray'] = None
		self.checks['chat'] = None
		self.checks['torrent'] = None
		self.checks['mail'] = None
		self.checks['nm'] = None
		self.checks['images'] = None
		self.checks['cdburner'] = None
		self.checks['filemanagaer'] = None
		self.checks['pdf'] = None
		self.checks['officesuits'] = None

		if not isdir(expanduser("~") + '/.config/openbox'):
			self.checks['tint2'] = False
		self.player = None
		self.app_pos = 15
		self.backend = 'openbox'

		## --- If you'd like to play sounds:


		self.active = None
		self.alive = 1

	def on_draw(self):
		self.render()

	def on_close(self):
		self.alive = 0

	def on_mouse_release(self, x, y, button, modifiers):
		self.active = None

	def on_mouse_press(self, x, y, button, modifiers):
		#count = 0
		for sprite_name, sprite in self.sprites.items():
			if sprite:
				if sprite.click(x, y):
					self.active = sprite
			#count += 1

	def on_mouse_drag(self, x, y, dx, dy, button, modifiers):
		if self.active:
			self.active.move(dx, dy)

	def on_key_press(self, symbol, modifiers):
		if symbol == 65307: # [ESC]
			self.alive = 0

	def draw_line(self, xy, dxy):
		glColor4f(0.2, 0.2, 0.2, 1)
		glBegin(GL_LINES)
		glVertex2f(xy[0], xy[1])
		glVertex2f(dxy[0], dxy[1])
		glEnd()

	def render(self):
		self.clear()
		self.bg.draw()
		if len(self.merge_sprites) > 0:
			installed_app = self.merge_sprites.popitem()
			self.sprites[installed_app[0]] = Spr(installed_app[1][0], installed_app[1][1])
			self.sprites[installed_app[0]].x = self.app_pos
			self.app_pos += 64+15
			self.sprites[installed_app[0]].y = self.height - 64-15

		glPointSize(25)
		glColor4f(0.2, 0.2, 0.2, 0.5)	
		glEnable(GL_BLEND)
		glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
		glBegin(GL_POINTS)
		for x in range(0,self.width+25,25):
			for y in range(0-64-15,0,25):
				glVertex3f(x, self.height+y, 0)
		glEnd()
		self.draw_line((0, self.height-64-26), (self.width, self.height-64-26))
		

		for sprite_name, sprite in self.sprites.items():
			if sprite and sprite_name != 'MsgBox':
				sprite._draw()

		if self.sprites['MsgBox']:
			self.sprites['MsgBox']._draw()

		if self.sprites['MsgBox'] and self.sprites['MsgBox'].Answer != None:
			if self.checks['SOUND'] == None:
				self.player.pause()
				self.checks['SOUND'] = self.sprites['MsgBox'].Answer
			elif self.checks['systray'] == None:
				self.checks['systray'] = self.sprites['MsgBox'].Answer
				with open(expanduser("~") + '/.config/openbox/autostart', 'ab') as fh:
					if self.checks['systray'] == 'tint2':
						fh.write('tint2 &\n')
						x = run('tint2 &')
						x.close()
					else:
						fh.write('cairo-dock -o &\n')
						x = run('cairo-dock -o &')
						x.close()
			elif self.checks['torrent'] == None:
				self.checks['torrent'] = self.sprites['MsgBox'].Answer
			elif self.checks['chat'] == None:
				self.checks['chat'] = self.sprites['MsgBox'].Answer
			elif self.checks['mail'] == None:
				self.checks['mail'] = self.sprites['MsgBox'].Answer
			elif self.checks['nm'] == None:
				self.checks['nm'] = self.sprites['MsgBox'].Answer

				# 'networkmanager', 'network-manager-applet'
			elif self.checks['images'] == None:
				self.checks['images'] = self.sprites['MsgBox'].Answer
			elif self.checks['cdburner'] == None:
				self.checks['cdburner'] = self.sprites['MsgBox'].Answer
			elif self.checks['filemanagaer'] == None:
				self.checks['filemanagaer'] = self.sprites['MsgBox'].Answer
			elif self.checks['pdf'] == None:
				self.checks['pdf'] = self.sprites['MsgBox'].Answer
			elif self.checks['officesuits'] == None:
				self.checks['officesuits'] = self.sprites['MsgBox'].Answer

			del self.sprites['MsgBox']
			self.sprites['MsgBox'] = None

		if not self.sprites['MsgBox']:
			if self.checks['SOUND'] == None:
				self.sprites['MsgBox'] = MsgBox('Sound check', 'Do you hear the sound playing? If not the default audio settings (ALSA) is not for you, for assistance please consult the forum at:\n\n - https://bbs.archlinux.org/')
				self.player = pyglet.media.Player()
				self.player.queue(pyglet.media.load('sound_check.wav'))
				self.player.play()

			elif self.checks['systray'] == None:
				options = ['cairo-dock', 'tint2']
				self.sprites['MsgBox'] = Select('Systray/Taskbar', 'OpenBox does not display running applications or the clock by default, select one of the following:', options, self.PacMan, True, True)
				self.sprites['MsgBox'].replace('cairo-dock', 'cairo-dock_screenie', 271, 124, 120)
				self.sprites['MsgBox'].replace('tint2', 'tint2_screenie', 600, 110, 60)

				#self.sprites['MsgBox'].add('3-tint2', Spr('./icons/tint2_screenie.png'), 15, 50)

			elif self.checks['torrent'] == None:
				options = []
				if self.backend == 'kde':
					options.append('kget')
					options.append('ktorrent')
				elif self.backend == 'gnome':
					pass # There are no specific gnome torrent client
				options.append('qbittorrent')
				#options.append('qtorrent') # <- Dead project (even thoe the packages are still present)
				options.append('transmission')
				options.append('tribler')
				#options.append('Vuze') # <- Honestly, a big honky application just eating up system performance.. (Sorry, another bad Java example)

				self.sprites['MsgBox'] = Select('Torrent client', 'When (/if) you download torrents, which applications do you use?', options, self.PacMan)

			elif self.checks['chat'] == None:
				self.sprites['MsgBox'] = Select('Chat applications', 'Which chat applications do you use?', ['skype', 'pidgin', 'irssi', 'xchat'], self.PacMan)

				#self.sprites['MsgBox'].add('3-tint2', Spr('./icons/skype.png', 64), self.sprites['MsgBox'].width/2-32, 50)
			elif self.checks['mail'] == None:
				options = []
				if self.backend == 'gnome':
					options.append('balsa')
					options.append('evolution') # <- Default in gnome					

				elif self.backend == 'kde':
					options.append('kmail')

				#elif self.backend == 'openbox':
				options.append('geary')# <- Uses gnome-keyring
				options.append('claws-mail')
				options.append('sylpheed')
				options.append('thunderbird')
				options.append('trojita')

				self.sprites['MsgBox'] = Select('Mail client', 'If you use a local mail-client, which would it be? (skip if you\'re using Gmail or Hotmail)', options, self.PacMan)

			elif self.checks['nm'] == None:
				# Connman <- One of the better, but requires additional applications for GUI and some settings.
				self.sprites['MsgBox'] = MsgBox('Network Manager', 'If you have WiFi on your PC you will probably need a network manager, would you like to install this one?\n\n\n * Supports:\n   - WiFi\n   - VPN (With passwords)\n   - "LAN"\n * Easy to use\n * Reconnects automaticly ',large=True)
				self.sprites['MsgBox'].add('3-nm', Spr('./icons/nm_screenie.png'), 15, 50)
				self.sprites['MsgBox'].draws['3-nm'].x = self.sprites['MsgBox'].width+70
				self.sprites['MsgBox'].draws['3-nm'].scale = 0.6
				
			elif self.checks['images'] == None:
				self.sprites['MsgBox'] = MsgBox('Image viewer', 'OpenBox has no built-in way to view images, so we ask you if you\'d like to install "Mirage"?')
				self.sprites['MsgBox'].add('3-mirage', Spr('./icons/mirage_screenie.png'), 15, 50)
			#elif self.checks['video'] == None:
			#	pass
			elif self.checks['cdburner'] == None:
				self.sprites['MsgBox'] = MsgBox('CD Burner', 'OpenBox has no built-in CD/DVD Burner app, so we ask you if you\'d like to install "Brasero"?')
				self.sprites['MsgBox'].add('3-brasero', Spr('./icons/brasero_screenie.png'), 15, 50)
			elif self.checks['filemanagaer'] == None:
				self.sprites['MsgBox'] = MsgBox('File manager', 'OpenBox has no built-in graphical "File Manager", would you like one called "Thunar"?')
				self.sprites['MsgBox'].add('3-thunar', Spr('./icons/thunar_screenie.png'), 15, 50)

				# There are a bunch of others, but i personally think this one is the most sleek and gives enough functionality to be useful via gvfs.
			elif self.checks['pdf'] == None:
				options = ['epdfview', 'qpdfview', 'xpdf'] # Chrome has support for it, it's clunky to get in via AUR but it could work.. read more into it.
				self.sprites['MsgBox'] = Select('PDF reader', 'Do you read PDF\'s? In that case, select a PDF viewer', options, self.PacMan)
				#self.sprites['MsgBox'].add('3-tint2', Spr('./icons/tint2_screenie.png'), 15, 50)
			elif self.checks['officesuits'] == None:
				self.sprites['MsgBox'] = MsgBox('Office Documents', 'Do you work with office documents? If so, would you like me to install LibreOffice?')
				self.sprites['MsgBox'].add('3-libreoffice', Spr('./icons/libre_screenie.png'), 15, 50)

			# https://wiki.archlinux.org/index.php/List_of_Applications


		self.flip()

	def run(self):
		while self.alive == 1:
			self.render()

			# -----------> This is key <----------
			# This is what replaces pyglet.app.run()
			# but is required for the GUI to not freeze
			#
			event = self.dispatch_events()


x = main()
x.run()