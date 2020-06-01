#!/usr/bin/python3
# /usr/bin/check_homeperm.py
# session required        pam_exec.so /usr/bin/check_homeperm.py
# chmod +x /usr/bin/check_homeperm.py

import os, stat

ADMINS_GID = 0
SHARE_DIRECTORY = 'upload_directory'
DOMAIN = 'example.com'

if not 'PAM_USER' in os.environ:
        exit(1)
if not 'XDG_RUNTIME_DIR' in os.environ:
        exit(2)

USER = os.environ['PAM_USER']
UID = int(os.path.basename(os.environ['XDG_RUNTIME_DIR']))

for root, folders, files in os.walk('/home'):
        for home_dir in folders:
                if f'{USER}@{DOMAIN}' == home_dir:
                        os.chown(os.path.abspath(f'{root}/{home_dir}/{SHARE_DIRECTORY}'), UID, ADMINS_GID)
                        os.chmod(os.path.abspath(f'{root}/{home_dir}/{SHARE_DIRECTORY}'), stat.S_IRUSR | stat.S_IXUSR | stat.S_IRWXG)
                        exit(0)
exit(1)
