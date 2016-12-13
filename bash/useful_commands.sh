find / -type f -name "$1" -exec ls -lh {} \; | awk '{ print $9 ": " $5 }'
