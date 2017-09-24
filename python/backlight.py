#!/usr/bin/python
"""
One useage example is with awesome window manager,
add the following to /etc/xdg/awesome/rc.lua:
    awful.key({ modkey,           }, "m",      function () awful.spawn("backlight.py") end,
              {description = "lock the screen", group="client"}),
"""

import sys
from subprocess import Popen, PIPE, STDOUT

new_bl = sys.argv[1] if len(sys.argv) > 1 else None

if new_bl is None:
        handle = Popen('xbacklight', shell=True, stdout=PIPE, stderr=STDOUT)
        while handle.poll() is None:
                pass

        output = handle.stdout.read().decode('UTF-8').strip()
        handle.stdout.close()

        backlight = int(float(output))
        if backlight > 0:
                new_bl = 0
        else:
                new_bl = 10

handle = Popen('xbacklight -set {bl}'.format(bl=new_bl), shell=True)
while handle.poll() is None:
        pass
