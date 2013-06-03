#!/bin/bash
#ffmpeg -v 1 -i $1 -c:v libx264 -crf 18 -preset slow -c:a copy "$1-youtube.mkv"
ffmpeg -v 1 -i $1 -c:v h263p -crf 18 -preset slow -c:a copy "$1-youtube.mkv"
