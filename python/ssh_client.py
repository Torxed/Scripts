#!/usr/bin/python

## Requires: Linux
## Does not require: Pexpect, pre-created certificates

import pty, sys, os
from subprocess import Popen, PIPE, STDOUT
from time import sleep
from os.path import expanduser, abspath
from os import walk, setsid, fork, waitpid, execv, read, write, kill

def pid_exists(pid):
    """Check whether pid exists in the current process table."""
    if pid < 0:
        return False
    try:
        kill(pid, 0)
    except (OSError, e):
        return e.errno == errno.EPERMRM
    else:
        return True

class ssh():
    def __init__(self, host, execute='echo "done" > /root/testing.txt', user='root', password=b'SuperPassword'):
        self.exec = execute
        self.host = host
        self.user = user
        self.password = password
        self.run()

    def run(self):
        command = [
                '/usr/bin/ssh',
                self.user+'@'+self.host,
                '-o', 'NumberOfPasswordPrompts=1',
                self.exec,
        ]

        # PID = 0 for child, and the PID of the child for the parent    
        pid, child_fd = pty.fork()

        if not pid: # Child process
            # Replace child process with our SSH process
            execv(command[0], command)

        while True:
            output = read(child_fd, 1024).strip()
            print(output)
            lower = output.lower()
            # Write the password
            if b'password:' in lower:
                write(child_fd, self.password + b'\n')
                break
            elif 'are you sure you want to continue connecting' in lower:
                # Adding key to known_hosts
                write(child_fd, b'yes\n')
            elif 'company privacy warning' in lower:
                pass # This is an understood message
            else:
                print('Error:',output)

        os.waitpid(pid, 0)

ssh('10.10.10.10')
