#!/usr/bin/env python

import argparse


default_config = '''

[Analysis]

# Instrument Response Function
irf = P8R2_SOURCE_V6

# Null-hyp probability
nullp = 1e-5

# Zenith cut for gtmktime
zenith_cut = 95

# Theta cut for gtmktime
theta_cut = 60

# Emin and emax in MeV
emin = 100
emax = 100000

# Maximum duration, above which any excess is excluded (in seconds)
Max_duration = 21600

# Minimum number of counts in excess
Min_counts = 3

[Post processing]
# Candidate transients within this distance from each other (in deg) will
# be checked and marked as the same transient if they overlap in time
cluster_distance = 15.0

[Real time]
# describes the type of database and the path to where it is stored. 
# See SQLAlchemy for more information about formatting

# if using sqlite set this to True - will create database at db_path, but do not need username, pword, etc
is_sqlite = False

# if not using sqlite, need this info
db_dialect = mysql
db_username = 
db_password = 
db_host = localhost
db_port = 3306

# regardless of database driver, need to know where to store the db!
db_path = database

# tolerance for ra, dec, start time, and interval when determining if two detections are the same
ra_tol = 1
dec_tol = 1
start_tol = 10
int_tol = 10

# real time will rerun all analyses that use data from start_interval to end_interval hours ago
# and an analysis on end_interval to the current time
start_interval = 24
end_interval = 12

# command to start an analysis on the farm
farm_command = qsub -l nodes=1:ppn=$NUM_CPUS -j oe -o $FARM_LOG_PATH -F ' --met_start $MET_START --duration $DURATION --counts $COUNTS --outfile $OUTFILE --logfile $LOGFILE --config $CONFIG' $SCRIPT

# path to where to store results
base_path = ./real_time_work

[Results email]
# Host server and port number for sending emails
host = ''
port = 0

# Login credentials for sending emails
username = ''

# Address to send the emails to and email subject heading
# for multiple recipients, use a comma separated list: person1@email.com,person2@email.com
recipient = ''
subject = ''

[Remote access]
# host with access to data accessed by mdcget.py
ssh_host = galprop-cluster

# path to setup file to allow mdcget.py to run 
source_path = ~/suli_jamie/jamie_setup.sh

# stores if we are at SLAC (False for at Stanford) 
at_slac = False

[Hardware]
ncpus = 10
'''


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Create a configuration file for the LAT Transient factory')

    parser.add_argument('--outfile', help="name for output configuration file", required=True)

    args = parser.parse_args()

    with open(args.outfile, 'w+') as f:

        f.write(default_config)
