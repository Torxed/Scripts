find / -type f -size +100000k -exec ls -lh {} \; | awk '{ print $9 ": " $5 }'
