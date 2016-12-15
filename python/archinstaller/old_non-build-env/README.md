Execution:
========
* Boot a live CD (and execute the following:)
* wget -O base.sh goo.gl/UVD2n (which points to [livecd.sh](livecd.sh))
* chmod +x base.sh
* ./base.sh


Notes:
======
This is a first release, the code is ugly to look at but it will work.<br>
Also, there will be more config options when running `install.py`. For now the only option is:<br>
* `python2 install.py --no-internet` - Will disable the internet check (if ICMP is not allowed)
