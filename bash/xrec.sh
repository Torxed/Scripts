#!/bin/bash
//if [ "$2" = "quality" ]; then
//	ffmpeg -v 1 -t 60 -f x11grab -s `xdpyinfo | grep 'dimensions:'|awk '{print $2}'` -r 30 -qscale 1 -i :0.0 -f alsa -i hw:0,0 -acodec flac -vcodec huffyuv -preset fast $1
//fi
//
//if [ "$2" = "stream" ]; then
//	ffmpeg -v 1 -t 30 -f x11grab -s `xdpyinfo | grep 'dimensions:'|awk '{print $2}'` -r 30 -qscale 1 -i :0.0 -f alsa -i hw:0,0 -acodec flac -vcodec h263p -preset fast $1
//fi
//
//if [ "$1" = "youtube" ]; then
//
//	ffmpeg \
//	 -i ./Downloads/best_of_vocal_trance_E89.mp3 \
//	 -f x11grab -s 1920x1080 -r 15 -i :0.0 \
//	 -c:v libx264 -preset fast \
//	 -c:a libmp3lame -ab 96k -ar 22050 \
//	 -threads 0 \
//	 -f flv youtube.flv
//
//fi

ffmpeg \
         -f x11grab -s 1920x1080 -r 15 -i :0.0 \
         -c:v libx264 -preset fast \
         -c:a libmp3lame -ab 96k -ar 22050 \
         -threads 0 \
         -f flv "$1.flv"
