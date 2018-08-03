#!/bin/bash

source ~/.bashrc

#Setup the MySQL port forwarding. Note that this will fail cleanly
#when the port forwarding is already active
export AUTOSSH_MAXLIFETIME=86400
export AUTOSSH_POLL=10
/storage/applications/autossh/build-1.4c/bin/autossh -f -M 5000 -L 3306:localhost:3306 -N galprop-cluster.stanford.edu

echo Done with first tunnel, starting second

#Setup SMTP port forwarding.
/storage/applications/autossh/build-1.4c/bin/autossh -f -M 5000 -L 65530:localhost:25 -N galprop-cluster.stanford.edu

echo Done with second tunnel, exiting

exit 0