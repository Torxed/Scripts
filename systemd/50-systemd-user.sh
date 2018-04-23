# Add to: /etc/X11/xinit/xinitrc.d/50-systemd-user.sh
systemctl --no-block --user start xsession.target

# And make sure this exists in /etc/X11/xinit/xinitrx:
#
# if [ -d /etc/X11/xinit/xinitrc.d ] ; then
#  for f in /etc/X11/xinit/xinitrc.d/?*.sh ; do
#   [ -x "$f" ] && . "$f"
#  done
#  unset f
# fi
