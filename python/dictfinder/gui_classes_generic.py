import pyglet
from pyglet.gl import *
from os.path import isfile

class Spr(pyglet.sprite.Sprite):
	def __init__(self, texture=None, width=None, height=None, color="#C2C2C2", alpha=int(0.2*255), x=None, y=None, anchor=None, moveable=True):
		if not texture or not isfile(texture):
			## If no texture was supplied, we will create one
			if not width:
				width = 220
			if not height:
				height = 450
			self.texture = self.gen_solid_img(width, height, color, alpha)
		else:
			self.texture = pyglet.image.load(texture)

		super(Spr, self).__init__(self.texture)

		self.anchor = anchor
		if anchor == 'center':
			self.image.anchor_x = self.image.width / 2
			self.image.anchor_y = self.image.height / 2
		if x:
			self.x = x
		if y:
			self.y = y

		self.moveable = moveable

	def gen_solid_img(self, width, height, c, alpha):
		c = c.lstrip("#")
		c = max(6-len(c),0)*"0" + c
		r = int(c[:2], 16)
		g = int(c[2:4], 16)
		b = int(c[4:], 16)
		c = (r,g,b,alpha)
		return pyglet.image.SolidColorImagePattern(c).create_image(width,height)

	def draw_line(self, xy, dxy, color=(0.2, 0.2, 0.2, 1)):
		glColor4f(color[0], color[1], color[2], color[3])
		glBegin(GL_LINES)
		glVertex2f(xy[0], xy[1])
		glVertex2f(dxy[0], dxy[1])
		glEnd()

	def draw_border(self, color=(0.2, 0.2, 0.2, 0.5)):
		self.draw_line((self.x, self.y), (self.x, self.y+self.height), color)
		self.draw_line((self.x, self.y+self.height), (self.x+self.width, self.y+self.height), color)
		self.draw_line((self.x+self.width, self.y+self.height), (self.x+self.width, self.y), color)
		self.draw_line((self.x+self.width, self.y), (self.x, self.y), color)

	def pixels_to_vertexlist(self, pixels):
		# Outdated pixel conversion code
		vertex_pixels = []
		vertex_colors = []

		for pixel in pixels:
			vertex = list(pixel)
			vertex_pixels += vertex[:-1]
			vertex_colors += list(vertex[-1])

		# Old pyglet versions (including 1.1.4, not including 1.2
		# alpha1) throw an exception if vertex_list() is called with
		# zero vertices. Therefore the length must be checked before
		# calling vertex_list().
		#
		# TODO: Remove support for pyglet 1.1.4 in favor of pyglet 1.2.
		if len(pixels):
			return pyglet.graphics.vertex_list(
				len(pixels),
				('v2i', tuple(vertex_pixels)),
				('c4B', tuple(vertex_colors)))
		else:
			return None

	def clean_vertexes(self, *args):
		clean_list = []
		for pair in args:
			clean_list.append((int(pair[0]), int(pair[1])))
		return clean_list

	def draw_square(self, bottom_left, top_left, top_right, bottom_right, color=(0.2, 0.2, 0.2, 0.5)):
		#glColor4f(0.2, 0.2, 0.2, 1)
		#glBegin(GL_LINES)

		bottom_left, top_left, top_right, bottom_right = self.clean_vertexes(bottom_left, top_left, top_right, bottom_right)

		c = (255, 255, 255, 128)

		window_corners = [
			(bottom_left[0],bottom_left[1],c),	# bottom left
			(top_left[0],top_left[1],c),	# top left
			(top_right[0],top_right[1],c),	# top right
			(bottom_right[0],bottom_right[1],c)		# bottom right
		]

		box_vl = self.pixels_to_vertexlist(window_corners)
		box_vl.draw(pyglet.gl.GL_QUADS)
		#glEnd()

	def draw_header(self):
		"""size = 15
			glPointSize(size)
			glColor4f(0.2, 0.2, 0.2, 0.5)
			glEnable(GL_BLEND)
			glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
			glBegin(GL_POINTS)
	
			for x in range(self.x, self.x+self.width+size, size):
				for y in range(self.y, self.y+self.height, size):
					glVertex2f(x, y)
			glEnd()"""
		self.draw_square((self.x, self.y), (self.x, self.y+self.height), (self.x+self.width, self.y+self.height), (self.x+self.width, self.y))

	def rotate(self, deg):
		self.image.anchor_x = self.image.width / 2
		self.image.anchor_y = self.image.height / 2
		self.rotation = self.rotation+deg
		if self.anchor != 'center':
			self.image.anchor_x = 0
			self.image.anchor_y = 0
		return True

	def fade_in(self):
		self.opacity += 10
		if self.opacity > 255:
			self.opacity = 255

	def fade_out(self):
		self.opacity -= 2.5
		if self.opacity < 0:
			self.opacity = 0

	def click_check(self, x, y):
		"""
		When called, returns self (the object)
		to the calling-origin as a verification
		that we pressed inside this object, and
		by sending back self (the object) the caller
		can interact with this object
		"""
		if x > self.x and x < (self.x + self.width):
			if y > self.y and y < (self.y + self.height):
				return self

	def click(self, x, y, merge):
		"""
		Usually click_check() is called followed up
		with a call to this function.
		Basically what this is, is that a click
		should occur within the object.
		Normally a class who inherits Spr() will create
		their own click() function but if none exists
		a default must be present.
		"""
		return True

	def right_click(self, x, y, merge):
		"""
		See click(), same basic concept
		"""
		return True

	def hover(self, x, y):
		"""
		See click(), same basic concept
		"""
		return True

	def hover_out(self, x, y):
		"""
		See click(), same basic concept
		"""
		return True

	def type(self, what):
		"""
		Type() is called from main() whenever a key-press
		has occured that is type-able.
		Meaning whenever a keystroke is made and it was
		of a character eg. A-Z it will be passed as a str()
		representation to type() that will handle the character
		in a given manner.
		This function doesn't process anything but will need
		to be here in case a class that inherits Spr() doesn't
		have their own function for it (which, they should...) 
		"""
		return True

	def gettext(self):
		return ''

	def move(self, x, y):
		if self.moveable:
			self.x += x
			self.y += y

	def _draw(self):
		"""
		Normally we call _draw() instead of .draw() on sprites
		because _draw() will contains so much more than simply
		drawing the object, it might check for interactions or
		update inline data (and most likely positioning objects).
		"""
		self.draw()