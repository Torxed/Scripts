import pyglet
from pyglet.gl import *
from gui_classes_generic import Spr
from collections import OrderedDict

class Input(Spr):
	def __init__(self, title='Test', pos=(0,0), width=None, height=None):
		if not title: return False
		super(Input, self).__init__(width=width, height=height, x=pos[0], y=pos[1])

		self.draws = {'1-title' : pyglet.text.Label(title, anchor_x='center', font_size=12, x=self.x+self.width/2, y=self.y+self.height-20)}
		self.input_cmd = pyglet.text.Label("", font_size=12, x=self.x+10, y=self.y+self.height/2-6)

	def type(self, c):
		self.input_cmd.text += c

	def gettext(self):
		return self.input_cmd.text

	def _draw(self):
		self.draw()
		self.draw_header()
		# top and bottom line:
		self.draw_line((self.x, self.y), (self.x+self.width, self.y))
		self.draw_line((self.x, self.y+self.height), (self.x+self.width, self.y+self.height))
		# left and right line:
		self.draw_line((self.x, self.y), (self.x, self.y+self.height))
		self.draw_line((self.x+self.width, self.y), (self.x+self.width, self.y+self.height))
		for obj in sorted(self.draws):
			self.draws[obj].draw()
		self.input_cmd.draw()

class TreeView(Spr):
	def __init__(self, main_spr, dictionary, align='left', padding_left=5, x=0, y=0, color='#FFFFFF', alpha=0):
		super(TreeView, self).__init__(width=main_spr.width, height=20, x=main_spr.x, y=y, color=color, alpha=alpha)
		self.padding_left = padding_left
		self.main_spr_x = main_spr.x
		self.main_spr_y = main_spr.y
		self.main_spr = main_spr

		self.draws = OrderedDict()
		y = self.y+self.height-20
		for key, val in dictionary.items():
			self.draws[key] = ListItem(self, key, dictionary[key], y=y)
			self.draws[key].move(self.x, y)
			y += 20

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
				for obj in self.draws:
					list_item = self.draws[obj]
					if x > list_item.x and x < (list_item.x+list_item.width):
						if y > list_item.y and y < (list_item.y+list_item.height):
							return list_item
				return self

	def move(self, x, y):
		self.x = x
		self.y = y

	def _draw(self):
		self.x = self.main_spr.x
		self.y = self.main_spr.y

		if self.main_spr.x != self.main_spr_x or self.main_spr.y != self.main_spr_y:
			self.x = self.main_spr.x
			self.y = self.main_spr.y
			self.main_spr_x = self.x
			self.main_spr_y = self.y

			y = self.y+self.height-20
			for obj in self.draws:
				self.draws[obj].move(self.x, y)
				y -= 20

			#self.scrollbar.move()
		else:
			for obj in self.draws:
				self.draws[obj]._draw()

		#self.scrollbar._draw()

		self.draw()

class ListItem(Spr):
	def __init__(self, main_spr, key, value, align='left', padding_left=5, y=0):
		super(ListItem, self).__init__(width=main_spr.width, height=20, x=main_spr.x, y=y)
		self.text = pyglet.text.Label(key, anchor_x='left', font_size=12, x=main_spr.x+padding_left, y=y+3)
		self.padding_left = padding_left

	def move(self, x, y):
		self.x = x
		self.y = y
		self.text.x = self.x+self.padding_left
		self.text.y = self.y+3

	def click(self, x, y, merges):
		print('Clicked on:', self.text.text)

	def _draw(self):
		self.draw()
		self.text.draw()

class ScrollBar(Spr):
	def __init__(self, main_spr, align='right'):
		super(ScrollBar, self).__init__(width=20, height=main_spr.height, x=main_spr.x+main_spr.width-20, y=main_spr.y)
		self.scroll_box = Spr(x=self.x, y=self.y, height=45, width=20)
		self.main_spr = main_spr

	def move(self):
		self.x=self.main_spr.x+self.main_spr.width-20
		self.y=self.main_spr.y

	def _draw(self):
		self.scroll_box._draw()
		self.draw()

class List(Spr):
	def __init__(self, main_spr, list_items={}, align='left', height=None, x=0, y=0):
		if not height or height < 20:
			height = 20*len(list_items)
			if height < 20:
				height = 20
		super(List, self).__init__(width=main_spr.width, height=height, x=x, y=y)
		self.main_spr = main_spr
		self.x = self.main_spr.x+x
		self.y = self.main_spr.y+y
		self.draws = {}
		y = self.y+self.height-20
		for key in list_items:
			self.draws[key] = ListItem(self, key, list_items[key], y=y)
			y -= 20

		self.scrollbar = ScrollBar(self)

		self.main_spr_x = main_spr.x
		self.main_spr_y = main_spr.y


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
				for obj in self.draws:
					list_item = self.draws[obj]
					if x > list_item.x and x < (list_item.x+list_item.width):
						if y > list_item.y and y < (list_item.y+list_item.height):
							return list_item
				return self

	def _draw(self):
		self.x = self.main_spr.x
		self.y = self.main_spr.y

		if self.main_spr.x != self.main_spr_x or self.main_spr.y != self.main_spr_y:
			self.x = self.main_spr.x
			self.y = self.main_spr.y
			self.main_spr_x = self.x
			self.main_spr_y = self.y

			y = self.y+self.height-20
			for obj in self.draws:
				self.draws[obj].move(self.x, y)
				y -= 20

			self.scrollbar.move()
		else:
			for obj in self.draws:
				self.draws[obj]._draw()

		self.scrollbar._draw()

class Menu(Spr):
	def __init__(self, main_spr, buttons={}, align='top'):
		if not main_spr: return False
		self.main_spr = main_spr
		self.align = align

		x = main_spr.x
		y = main_spr.y
		if self.align=='top':
			y += main_spr.height-20

		super(Menu, self).__init__(width=main_spr.width, height=20, x=x, y=y)
		self.draws = {}
		for obj in buttons:
			self.draws['2-' + obj] = pyglet.text.Label(obj, anchor_x='left', font_size=12, x=x+5, y=y+4, color=(0,0,0,255))
			x += len(obj)*12

		self.main_spr_x = main_spr.x
		self.main_spr_y = main_spr.y

	def _draw(self):
		self.draw_header()
		if self.main_spr.x != self.main_spr_x or self.main_spr.y != self.main_spr_y:
			x = self.x = self.main_spr.x
			self.y = self.main_spr.y
			self.main_spr_x = self.x
			self.main_spr_y = self.y

			if self.align=='top':
				self.y += self.main_spr.height-20
			for obj in self.draws:
				self.draws[obj].x = x
				self.draws[obj].y = self.y
				self.draws[obj].draw()
				x += len(obj)*10
		else:
			for obj in sorted(self.draws):
				self.draws[obj].draw()

	def move(self, x, y):
		return False
		## If movable:
		#self.x += x
		#self.y += y
		#for obj in self.draws:
		#	self.draws[obj].x += x
		#	self.draws[obj].y += y