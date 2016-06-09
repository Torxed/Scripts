#!/bin/bash

if [ "$1" = "dock" ]
    then
            xrandr --output DP2-1 --mode 2560x1440 --right-of eDP2 --output DP2-2 --mode 2560x1440 --right-of DP2-1
fi
