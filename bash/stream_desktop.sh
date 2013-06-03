#!/bin/bash
#ffmpeg -re -y -loglevel warning -f x11grab -i :0.0 -r 30 -s 1920x1080 \
# -threads 2 -vcodec libx264 -threads 0 \
# -f mpegts udp://10.0.0.138:1234

#pcm_s32le
#libmp3lame

# record mic:
# -f alsa -ac 2 -i hw:0 -acodec pcm_s32le -aq 1 -ab 128k \
# record radio-stream:
# -i http://pub1.di.fm:80/di_vocaltrance \
# record local mp3:

ffmpeg \
 -i ./Downloads/best_of_vocal_trance_E89.mp3 \
 -f x11grab -s 1920x1080 -r 15 -i :0.0 \
 -c:v libx264 -preset fast -pix_fmt yuv420p -s 1280x800 \
 -c:a libmp3lame -ab 96k -ar 22050 \
 -threads 0 \
 -vf "movie=./torxed_overlay.png [watermark]; [in][watermark] overlay=10:10 [out]" \
 -f flv "rtmp://live.twitch.tv/app/live_id"
