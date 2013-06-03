#!/bin/bash

ffmpeg -i http://pub1.di.fm:80/di_vocaltrance -f alsa -ac 2 -i hw:0 -acodec pcm_s32le -aq 1 -ab 128k -f x11grab -s 1920x1080 -r 15 \
 -i :0.0 -c:v libx264 -preset fast \
 -pix_fmt yuv420p -s 1280x800 -c:a libmp3lame -ab 96k -ar 22050 \
 -threads 0 \
 -vf "movie=./Downloads/cat.png [watermark]; [in][watermark] overlay=10:10 [out]"  -f flv \
 -y test.flv
