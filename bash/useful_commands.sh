// Find a specific file/wildcard and output the size.
find / -type f -name "$1" -exec ls -lh {} \; | awk '{ print $9 ": " $5 }'
// List the 10 largest files from within the current directory.
for i in G M K; do du -ah | grep [0-9]$i | sort -nr -k 1; done | head -n 11
