import pyglet
from math import pi, sin, cos
from time import sleep, time
from os import _exit
from pyglet.gl import *

# == Useful links
# https://groups.google.com/forum/#!topic/pyglet-users/NYphQ_HoNYk
# http://www.opengl.org/documentation/specs/glut/spec3/node81.html
# http://fly.cc.fer.hr/~unreal/theredbook/chapter04.html
# http://www.opengl.org/sdk/docs/man2/xhtml/glVertexPointer.xml

 
def hextoint(i):
	if i > 255:
		i = 255
	return (1.0/255.0) * i

def setup():
	# One-time GL setup
	#glClearColor(1, 1, 1, 1)
	#glColor3f(hextoint(0), hextoint(0), hextoint(0))
	#glEnable(GL_DEPTH_TEST)
	glEnable(GL_CULL_FACE)

	# Uncomment this line for a wireframe view
	#glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

	# Simple light setup.  On Windows GL_LIGHT0 is enabled by default,
	# but this is not the case on Linux or Mac, so remember to always 
	# include it.
	glEnable(GL_LIGHTING)
	glEnable(GL_LIGHT0)
	glEnable(GL_LIGHT1)

	# Define a simple function to create ctypes arrays of floats:
	def vec(*args):
		return (GLfloat * len(args))(*args)

	glLightfv(GL_LIGHT0, GL_POSITION, vec(.5, .5, 1, 0))
	glLightfv(GL_LIGHT0, GL_SPECULAR, vec(.5, .5, 1, 1))
	glLightfv(GL_LIGHT0, GL_DIFFUSE, vec(1, 1, 1, 1))
	glLightfv(GL_LIGHT1, GL_POSITION, vec(1, 0, .5, 0))
	glLightfv(GL_LIGHT1, GL_DIFFUSE, vec(.5, .5, .5, 1))
	glLightfv(GL_LIGHT1, GL_SPECULAR, vec(1, 1, 1, 1))

	glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(hextoint(30), hextoint(30), hextoint(30), hextoint(255)))
	glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, vec(1, 1, 1, 1))
	glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 10)

	glTranslatef(0, 0, -200)

class Circle(object):
	def __init__(self, posx=0, posy=0, radius=1, sides=35):
		self.list = glGenLists(1)
		glNewList(self.list, GL_COMPILE)
		glBegin(GL_POLYGON)
		for i in range(sides):
			#i = p i*2, *2=r^2
			x=radius * cos(i*2*pi/sides)+posx
			y=radius * sin(i*2*pi/sides)+posy
			glVertex2f(x,y)
		#math : P=pr^2=p*r*r= p*r*2 programming i*2*pi/sides together : i = p i*2, *2=r^2 this should help you
		glEnd()
		glEndList()
	def draw(self):
		glCallList(self.list)

class Ball(object):
	def __init__(self, sides=32):
		glColor3f(1.0, 0.3, 0.3) #set ball colour
		self.sphere = gluNewQuadric()
		gluSphere(self.sphere, 12.0, sides, sides-8)
		glTranslatef(-1,0,0)
		glMatrixMode(GL_MODELVIEW)


	def draw(self):
		print(dir(self.sphere))

class Torus(object):
	def __init__(self, radius, inner_radius, slices, inner_slices):
		# Create the vertex and normal arrays.
		vertices = []
		normals = []

		u_step = 2 * pi / (slices - 1)
		v_step = 2 * pi / (inner_slices - 1)
		u = 0.
		for i in range(slices):
			cos_u = cos(u)
			sin_u = sin(u)
			v = 0.
			for j in range(inner_slices):
				cos_v = cos(v)
				sin_v = sin(v)

				d = (radius + inner_radius * cos_v)
				x = d * cos_u
				y = d * sin_u
				z = inner_radius * sin_v

				nx = cos_u * cos_v
				ny = sin_u * cos_v
				nz = sin_v

				vertices.extend([x, y, z])
				normals.extend([nx, ny, nz])
				v += v_step
			u += u_step

		# Create ctypes arrays of the lists
		vertices = (GLfloat * len(vertices))(*vertices)
		normals = (GLfloat * len(normals))(*normals)

		# Create a list of triangle indices.
		indices = []
		for i in range(slices - 1):
			for j in range(inner_slices - 1):
				p = i * inner_slices + j
				indices.extend([p, p + inner_slices, p + inner_slices + 1])
				indices.extend([p,  p + inner_slices + 1, p + 1])
		indices = (GLuint * len(indices))(*indices)

		# Compile a display list
		self.list = glGenLists(1)
		glNewList(self.list, GL_COMPILE)

		glPushClientAttrib(GL_CLIENT_VERTEX_ARRAY_BIT)
		glEnableClientState(GL_VERTEX_ARRAY)
		glEnableClientState(GL_NORMAL_ARRAY)
		glVertexPointer(3, GL_FLOAT, 0, vertices)
		glNormalPointer(GL_FLOAT, 0, normals)
		glDrawElements(GL_TRIANGLES, len(indices), GL_UNSIGNED_INT, indices)
		glPopClientAttrib()

		glEndList()

	def draw(self):
		glCallList(self.list)

class vertex():
	def __init__(self):
		self.obj = pyglet.graphics.vertex_list(2,
			('v2i', (10, 15, 30, 35)),
			('c3B', (0, 0, 255, 0, 255, 0))
		)

class gui (pyglet.window.Window):
	def __init__ (self, width=1200, height=900):
		super(gui, self).__init__(650, 450, vsync=True, fullscreen = False, resizable=True, config=Config(sample_buffers=1, samples=4, depth_size=16, double_buffer=True,))

		self.colorscheme = {
			'background' : (hextoint(0), hextoint(0), hextoint(0), hextoint(255))
		}
		glClearColor(*self.colorscheme['background'])
		self.set_location(650,300)
		self.alive = 1
		self.click = None
		self.drag = False
		self.keystates = {}

		#self.test = vertex()
		setup()

		self.toruses = []
		for i in range(0, 20, 4):
			self.toruses.append(Circle(0, i, 5))

		self.rx = self.ry = self.rz = 0

		self.framerate = 0.010

		self.fps = 0
		self.lastmeasurepoint = time()
		self.fr = pyglet.text.Label(text='calculating fps', font_name='Verdana', font_size=8, bold=False, italic=False,
										color=(255, 255, 255, 255), x=10, y=8,
										anchor_x='left', anchor_y='baseline',
										multiline=False, dpi=None, batch=None, group=None)

	#def update(self, dt):
	#	self.rx += dt * 1
	#	self.ry += dt * 80
	#	self.rz += dt * 30
	#	self.rx %= 360
	#	self.ry %= 360
	#	self.rz %= 360

	def on_resize(self, width, height):
		# Override the default on_resize handler to create a 3D projection
		glViewport(0, 0, width, height)
		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		gluPerspective(60., width / float(height), .1, 1000.)
		glMatrixMode(GL_MODELVIEW)
		return pyglet.event.EVENT_HANDLED

	def on_close(self):
		print('closing')
		self.alive = 0

	def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
		if self.click:
			self.drag = True
		self.rx += dx
		self.ry += dy
		self.rz += dy
		self.rx %= 360
		self.rz %= 360

	def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
		glTranslatef(0, 0, scroll_y*10)

	def on_mouse_press(self, x, y, button, modifiers):
		pass #print button

	def on_mouse_release(self, x, y, button, modifiers):
		self.click = None
		self.drag = False

	def on_key_press(self, symbol, modifiers):
		if symbol == 65307:
			self.alive = 0
		elif symbol == 32:
			self.rx = self.ry = self.rz = 0
			glLoadIdentity()
			glTranslatef(0, 0, -200)
		else:
			self.keystates[symbol] = True
			#print symbol

	def on_key_release(self, symbol, modifiers):
		self.keystates[symbol] = False

	def render(self):
		#glLoadIdentity()
		#glTranslatef(0, 0, -200)
		self.clear()
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

		#glLoadIdentity()
		#glTranslatef(0, 0, 0)
		#glRotatef(self.rz, 0, 0, 1)
		#glRotatef(self.ry, 0, 1, 0)
		#glRotatef(self.rx, 1, 0, 0)
		for torus in self.toruses:
			torus.draw()
			
		self.fr.draw()
		Ball()
		#self.test.obj.draw(pyglet.gl.GL_LINES)
		#self.bg.blit(0,0)

	def run(self):
		while self.alive == 1:
			event = self.dispatch_events()

			if 65362 in self.keystates and self.keystates[65362] > 0:# up
				self.rx -= 0.25
				#self.rx %= 360
				glRotatef(self.rx%360, 1, 0, 0)	
			if 65363 in self.keystates and self.keystates[65363] > 0:# right
				self.ry -= 0.25
				#self.ry %= 360
				glRotatef(self.ry%360, 0, 1, 0)
			if 65364 in self.keystates and self.keystates[65364] > 0:# down
				self.rx += 0.25
				#self.rx %= 360
				glRotatef(self.rx%360, 1, 0, 0)	
			if 65361 in self.keystates and self.keystates[65361] > 0:# left
				self.ry += 0.25
				#self.ry %= 360
				glRotatef(self.ry%360, 0, 1, 0)
			if 122 in self.keystates and self.keystates[122] > 0: # z
				self.rz += 0.25
				glRotatef(self.rz%360, 0, 0, 1)

			self.render()
			self.flip()
			self.fps += 1
			if time() - self.lastmeasurepoint >= 1:
				self.fr.text = str(self.fps) + 'fps'
				self.fps = 0
				self.lastmeasurepoint = time()
			sleep(self.framerate)
 
g = gui()
g.run()
