import ctypes
import ctypes.wintypes
import struct
import time
import pyglet
from ctypes.wintypes import (BOOL, DOUBLE, DWORD, HBITMAP, HDC, HGDIOBJ,  # noqa
								 HWND, INT, LPARAM, LONG, UINT, WORD)  # noqa

## HELP: https://stackoverflow.com/questions/17394685/screenshot-ctypes-windll-createdcfromhandle
# Modded from: https://github.com/flexxui/flexx/blob/master/flexx/util/screenshot.py
# And copied from: https://github.com/python-pillow/Pillow/blob/2b87ccae896c0b35a1215f2d454ffe4c547e7d93/src/display.c

SRCCOPY = 0xCC0020  # Code de copie pour la fonction BitBlt()
CAPTUREBLT = 0x40000000
DIB_RGB_COLORS = BI_RGB = 0
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL,
								 ctypes.wintypes.HWND,
								 ctypes.wintypes.LPARAM)

class BITMAPINFOHEADER(ctypes.Structure):
	_fields_ = [('biSize', DWORD), ('biWidth', LONG), ('biHeight', LONG),
				('biPlanes', WORD), ('biBitCount', WORD),
				('biCompression', DWORD), ('biSizeImage', DWORD),
				('biXPelsPerMeter', LONG), ('biYPelsPerMeter', LONG),
				('biClrUsed', DWORD), ('biClrImportant', DWORD)]

class BITMAPINFO(ctypes.Structure):
	_fields_ = [('bmiHeader', BITMAPINFOHEADER), ('bmiColors', DWORD * 3)]

# 1864
class WindowsWindow():
	def __init__(self, hwnd, x, y, w, h):
		self.hwnd = hwnd
		self.x = x
		self.y = y
		self._width = w
		self._height = h

	@property
	def width(self):
		return int(self._width * 1.5)
	
	@property
	def height(self):
		return int(self._height * 1.5)
	

	def __repr__(self):
		return f"<Window {self.hwnd} @ x: {self.x}, y: {self.y}, width: {self.width}, height: {self.height}>"

def GetWindowRectFromName(name:str, include_window_decoration=False, padd_for_header=True)-> tuple:
	hwnd = ctypes.windll.user32.FindWindowW(0, name)
	rect = ctypes.wintypes.RECT()
	padding=0
	if include_window_decoration:
		ctypes.windll.user32.GetWindowRect(hwnd, ctypes.pointer(rect))
	else:
		ctypes.windll.user32.GetClientRect(hwnd, ctypes.pointer(rect))

	if padd_for_header:
		padding += 46

	if hwnd:
		return WindowsWindow(hwnd, rect.left, rect.top+padding, rect.right-rect.left, rect.bottom-rect.top)

#def get_monitor():
#	rect = ctypes.wintypes.RECT()
#	monitorDC = ctypes.windll.gdi32.CreateDCW("DISPLAY", None, None, None)
#	ctypes.windll.user32.GetClientRect(monitorDC, ctypes.pointer(rect))
#	return WindowsWindow(monitorDC, rect.left, rect.top, rect.right-rect.left, rect.bottom-rect.top)

def screenshot(WindowsWindow_Obj):# target_hwnd, x, y, width, height):
	x, y = WindowsWindow_Obj.x, WindowsWindow_Obj.y
	height, width = WindowsWindow_Obj.height, WindowsWindow_Obj.width
	RASTER_OPTIONS = SRCCOPY
	buffer_len = height * width * 4

	#hwndDC = ctypes.windll.user32.GetWindowDC(WindowsWindow_Obj.hwnd)
	hwndDC = ctypes.windll.gdi32.CreateDCW("DISPLAY", None, None, None)

	saveDC = ctypes.windll.gdi32.CreateCompatibleDC(hwndDC)
	bitmap = ctypes.windll.gdi32.CreateCompatibleBitmap(hwndDC, width, height)
	ctypes.windll.gdi32.SelectObject(saveDC, bitmap)

	ctypes.windll.user32.PrintWindow(WindowsWindow_Obj.hwnd, saveDC, 0)

	bmi = BITMAPINFO()
	bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
	bmi.bmiHeader.biWidth = width
	bmi.bmiHeader.biHeight = height
	bmi.bmiHeader.biPlanes = 1 # bcPlanes has to be one according to https://docs.microsoft.com/en-us/windows/win32/api/wingdi/ns-wingdi-bitmapcoreheader
	bmi.bmiHeader.biBitCount = 32 # Because we're capturing BGRX (not sure how to avoid this, but 24 would be more logical?)
	bmi.bmiHeader.biCompression = BI_RGB

	image = ctypes.create_string_buffer(buffer_len)
	ctypes.windll.gdi32.BitBlt(saveDC, 0, 0, width, height, hwndDC, x, y, RASTER_OPTIONS)
	image_line_count = ctypes.windll.gdi32.GetDIBits(saveDC, bitmap, 0, height, image, bmi, DIB_RGB_COLORS)
	assert image_line_count == height

	# Replace pixels values: BGRX to RGB
	image2 = ctypes.create_string_buffer(height*width*3)
	image2[0::3] = image[2::4]
	image2[1::3] = image[1::4]
	image2[2::3] = image[0::4]

	ctypes.windll.gdi32.DeleteObject(hwndDC)
	ctypes.windll.gdi32.DeleteObject(saveDC)
	ctypes.windll.gdi32.DeleteObject(bitmap)

	return image2

class main(pyglet.window.Window):
	def __init__ (self, width=800, height=600, fps=False, *args, **kwargs):
		#game_window = GetWindowRectFromName("Forager by HopFrog")
		game_window = GetWindowRectFromName("Films & TV")

		super(main, self).__init__(game_window.width, game_window.height, *args, **kwargs)
		self.x, self.y = 0, 0
		self.game_window = game_window

		print(self.game_window)
		self.pixels = pixels = b"\x00" * (self.game_window.width * self.game_window.height * 3)
		self.pitch = self.game_window.width*3

		self.keys = {}
		self.alive = 1

	def on_draw(self):
		self.render()

	def on_close(self):
		self.alive = 0

	def on_key_release(self, symbol, modifiers):
		try:
			del self.keys[symbol]
		except:
			pass

	def on_key_press(self, symbol, modifiers):
		if symbol == pyglet.window.key.ESCAPE: # [ESC]
			self.alive = 0

		self.keys[symbol] = True

	def render(self):
		self.clear()

		try:
			self.pixels = screenshot(self.game_window)
		except ctypes.ArgumentError:
			pass
		image_data = pyglet.image.ImageData(self.game_window.width, self.game_window.height, 'RGB', self.pixels, self.pitch)
		self.image = pyglet.sprite.Sprite(image_data)
		
		self.image.draw()

		self.flip()

	def run(self):
		while self.alive == 1:
			self.render()

			# -----------> This is key <----------
			# This is what replaces pyglet.app.run()
			# but is required for the GUI to not freeze
			#
			event = self.dispatch_events()

if __name__ == '__main__':
	x = main()
	x.run()
