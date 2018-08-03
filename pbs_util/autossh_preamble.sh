#!/bin/bash

#source ~/.bashrc

#Setup the MySQL port forwarding. Note that this will fail cleanly
#when the port forwarding is already active
export AUTOSSH_MAXLIFETIME=86400
export AUTOSSH_POLL=10
/home/ltf_blind/autossh/build-1.4f/bin/autossh -f -M 5123 -L 3306:localhost:3306 -N galprop-cluster.stanford.edu || echo "Couldn't open MySQL tunnel. Maybe already open?"

#Setup SMTP port forwarding.
/home/ltf_blind/autossh/build-1.4f/bin/autossh -f -M 5124 -L 65530:localhost:25 -N galprop-cluster.stanford.edu || echo "Couldn't open SMTP tunnel. Maybe already open?"


exit 0

