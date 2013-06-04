Execution:
========
* Boot a live CD (and execute the following:)
* pacman -Syu
* pacman -S python2
* wget [https://raw.github.com/Torxed/Scripts/master/python/archinstaller/install.py](install.py)
* wget [https://raw.github.com/Torxed/Scripts/master/python/archinstaller/inside_install.py](inside_install.py)
* python2 install.py


Notes:
======
This is a first release, the code is ugly to look at but it will work.<br>
Also, there will be more config options when running `install.py`. For now the only option is:<br>
* `python2 install.py --no-internet` - Will disable the internet check (if ICMP is not allowed)
