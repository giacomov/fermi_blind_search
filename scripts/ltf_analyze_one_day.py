#!/usr/bin/env python

#PBS -l walltime=04:00:00
#PBS -l nodes=1:ppn=10
#PBS -l vmem=30gb


import datetime
import socket

import os
import shutil
import subprocess
import sys
import traceback


def are_we_at_slac():
    hostname = socket.getfqdn()

    if hostname.find('slac.stanford.edu') > 0:

        return True
    else:

        return False


def make_analysis(date, duration, config_file, workdir, outfile):
    cmd_line = ("ltf_search_for_transients.py --date %sT00:00:00 --duration %s --config %s "
                "--workdir %s --outfile %s" % (date, duration, config_file, workdir, outfile))

    print(cmd_line)

    subprocess.check_call(cmd_line, shell=True)


if __name__ == "__main__":

    # Process command line

    date, duration, config_file, outdir = sys.argv[1:]

    # Print options
    print("About to execute job with these parameters:\n")
    print("date : %s" % date)
    print("duration : %s" % duration)

    print("\n\n\nRunning on the computer farm")
    print("This is my environment:")
    for key, value in os.environ.iteritems():
        print("%s = %s" % (key, value))

    # Print 3 empty lines
    print("\n\n\n")

    # This is what you need to do to create a directory
    # in the computer node

    # This is your unique job ID (a number like 546127)

    if are_we_at_slac():

        unique_id = os.environ.get("LSB_JOBID")

        workdir = os.path.join('/scratch', unique_id)

    else:

        unique_id = os.environ.get("PBS_JOBID").split(".")[0]

        # os.path.join joins two path in a system-independent way
        workdir = os.path.join('/dev/shm', unique_id)

    # Now create the workdir
    print("About to create %s..." % (workdir))

    try:
        os.makedirs(workdir)
    except:
        print("Could not create workdir %s !!!!" % (workdir))
        raise
    else:
        # This will be executed if no exception is raised
        print("Successfully created %s" % (workdir))

    # now you have to go there
    os.chdir(workdir)

    # Name for output file
    dt = datetime.datetime.strptime(date, "%Y-%m-%d")
    outfile = dt.strftime("%y%m%d_res.txt")

    try:

        make_analysis(date, duration, config_file, workdir, outfile)

    except:

        traceback.print_exc(sys.stdout)

    else:

        # Copy back results
        shutil.copy2(outfile, outdir)

    finally:

        # This is executed in any case, whether an exception have been raised or not
        # I use this so we are sure we are not leaving trash behind even
        # if this job fails

        # First move out of the workdir
        os.chdir(os.path.expanduser('~'))

        # Now remove the directory
        try:

            shutil.rmtree(workdir)

        except:

            print("Could not remove workdir. Unfortunately I left behind some trash!!")
            raise

        else:

            print("Clean up completed.")
