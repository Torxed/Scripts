from math import *
from pyglet.gl import *

config = Config(sample_buffers=1, samples=4, 
					depth_size=16, double_buffer=True,)
window = pyglet.window.Window(config=config)

def makeCircle(numPoints, size=100, degrees=360, start=0, end=None, endpoint=False):
	verts = []
	pad_x = 300
	pad_y = 250
	if not end: end = degrees
	for i in range(numPoints):
		angle = radians(float(i)/numPoints * float(degrees))
		if angle < radians(float(start)): continue
		if angle > radians(float(end)): continue

		x = size*cos(angle) + pad_x
		y = size*sin(angle) + pad_y
		verts += [x,y]

	if endpoint:
		verts += [0+pad_x,0+pad_y]
	return pyglet.graphics.vertex_list(int(len(verts)/2), ('v2f', verts))

#GL_LINE_STRIP

circles = []
circles.append(makeCircle(36, 110, 360, 0, 100, True))
circles.append(makeCircle(36, 130, degrees=360, start=100, end=140, endpoint=True))
#circles.append(makeCircle(36, 120, degrees=360, start=0, end=100, endpoint=True))
#circles.append(makeCircle(36, 120, degrees=360, start=0, end=100, endpoint=True))
#circles.append(makeCircle(36, 120, degrees=360, start=0, end=100, endpoint=True))
#circles.append(makeCircle(36, 120, degrees=360, start=0, end=100, endpoint=True))
circles.append(makeCircle(36))

@window.event
def on_draw():
	global circles
	glClear(pyglet.gl.GL_COLOR_BUFFER_BIT)
	glColor3f(1,1,1)
	for circle in circles:
		circle.draw(GL_LINE_LOOP)

pyglet.app.run()
