## Will download the x86_64 branch of ArchLinux
## from liu.se and also additional AUR packages.

HOST="ftp.lysator.liu.se"

SOURCE="rsync://$HOST/pub/archlinux"
DEST='/tmp/mirrors/archlinux'
BW_LIMIT='5000' #kb/s
REPOS='core extra community'
RSYNC_OPTS="-rtlHq --delete-after --delay-updates --copy-links --safe-links --max-delete=1000 --bwlimit=${BW_LIMIT} --delete-excluded --exclude=i686"
LCK_FLE='/var/run/arc_repo-sync.lck'

PATH='/usr/bin'

# Make sure only 1 instance runs
if [ -e "$LCK_FLE" ] ; then
	OTHER_PID=$(cat $LCK_FLE)
	echo "Another instance already running: $OTHER_PID"
	exit 1
fi
echo $$ > "$LCK_FLE"

for REPO in $REPOS ; do
	echo "Syncing $REPO into $DEST"
	mkdir -p ${DEST}
	rsync $RSYNC_OPTS ${SOURCE}/${REPO} ${DEST}
done

wget https://aur.archlinux.org/cgit/aur.git/snapshot/sublime-text.tar.gz -O ${DEST}/sublime-text.tar.gz

# Cleanup
rm -f "$LCK_FLE"

exit 0
