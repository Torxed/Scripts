#!/bin/bash
sudo mount /dev/sdb /mnt/usb; sudo cp ~/Downloads/$(ls -t ~/Downloads/ | head -n 1) /mnt/usb/; sync; sudo umount /mnt/usb;
