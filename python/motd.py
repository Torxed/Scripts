#!/usr/bin/python
#->/etc/pam.d/system-login:
#   session    optional   pam_exec.so          /usr/bin/motd.py
#   session    optional   pam_motd.so          motd=/etc/motd

motd_message = """

    Useful paths:
    =============

    /srv/http         - Web server directory
    /srv/http/vhosts  - Web-site content directories

    /srv/http/server.py - Runs the web+dns server instance

    (To add new domain names, talk to anton because the DNS is turned off)


"""
with open('/etc/motd', 'w') as motd:
        motd.write(motd_message)