#!/bin/bash

qvm-ls -n | awk -F '|' '{print $1,$5}' | {
	while IFS= read -r line
	do
		name=$(echo $line | cut -f1 -d ' ' | grep -o "[-0-9a-zA-Z_]\+")
		type=$(echo $line | cut -f2 -d ' ')
		if [[ $line == -* || $line == *name* || $line == *dom0* ]] ;
		then
			continue
		else
			echo "Shutting down $name"

			if [[ $type == HVM ]] ;
			then
				qvm-kill $name &
			else
				# Fancy way of shutting down:
				/usr/lib/qubes/qrexec-client -d $name root:"shutdown -hP now" &

				# You could save you all this coding trouble with
				# the following command, but that doesn't work on some VMs
				# qvm-run --all "shutdown -hP now"				
			fi
		fi
	done
}
