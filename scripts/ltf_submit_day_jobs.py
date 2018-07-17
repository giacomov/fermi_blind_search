#!/usr/bin/env python
import argparse
import datetime
import os
import sys
import socket
import subprocess


from fermi_blind_search.which import which
from fermi_blind_search.configuration import get_config

def are_we_at_slac():
    
    hostname = socket.getfqdn()
    
    if hostname.find('slac.stanford.edu') > 0:
        
        return True
    else:
        
        return False


def valid_date(s):

    try:

        return datetime.datetime.strptime(s, "%Y-%m-%d")

    except ValueError:

        msg = "Not a valid date: '{0}'.".format(s)

        raise argparse.ArgumentTypeError(msg)


# def valid_configuration(s):
#
#     # Set environment
#     os.environ['LTF_CONFIG_FILE'] = s
#
#     # Get configuration
#     from fermi_blind_search.configuration import configuration
#
#     return configuration


def range_of_dates(start_date, end_date):

    # A generator for days between the two provided dates

    if start_date <= end_date:

        for n in range( ( end_date - start_date ).days + 1 ):

            yield start_date + datetime.timedelta(n)

    else:

        for n in range( ( start_date - end_date ).days + 1 ):

            yield start_date - datetime.timedelta(n)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Generate LTF jobs (one job per day) between two dates, and submit '
                                                 'them to the farm')

    parser.add_argument('--start_date', help='''Start date in ISO format. Ex: "2010-12-31" "''',
                        type=valid_date, required=True)
    parser.add_argument('--end_date', help='''End date in ISO format. Ex: "2010-12-31" "''',
                        type=valid_date, required=True)
    parser.add_argument('--config', help="Path to configuration file",
                        type=get_config, required=True)
    parser.add_argument('--outdir', help="Directory for results (must be on NFS/AFS)",
                        type=str, required=True)
    parser.add_argument('--logdir', help="Directory for logs (must be on NFS/AFS)",
                        type=str, required=True)
    parser.add_argument('--simulate', help="If active, do not submit jobs, just print the commands",
                        action="store_true")
    args = parser.parse_args()
    
    date_range = range_of_dates(args.start_date, args.end_date)

    # Print a summary
    print("\nProcessing 1-day jobs between %s and %s" % (args.start_date.isoformat(),
                                                       args.end_date.isoformat()))
    print("Current configuration:\n")
    args.config.write(sys.stdout)

    _ = raw_input("\nHit enter to continue, or crtl-c to stop")

    # Create output and logs directory, if they do not exists
    outdir = os.path.abspath(os.path.expandvars(os.path.expanduser(args.outdir)))
    logdir = os.path.abspath(os.path.expandvars(os.path.expanduser(args.logdir)))

    if not os.path.exists(outdir):

        os.makedirs(outdir)

    if not os.path.exists(logdir):

        os.makedirs(logdir)

    # Find where the executable ltf_analyze_one_day is
    ltf_analyze_one_day_script_path = which("ltf_analyze_one_day.py")

    i = -1

    for i, date in enumerate(date_range):
        
        #2015-09-14T09:50:45 86400.0 P8R2_TRANSIENT010E_V6 1e-6

        logfile_root = date.strftime("%y%m%d")  # this is like 100101 for 2010-01-01

        logfile_path = os.path.join(logdir, "%s.log" % logfile_root)

        if are_we_at_slac():
             
            cmd_line = ('''bsub -W 03:00 -Rinet -n 4 -R "span[hosts=1] rusage[mem=1000]"'''
                        ''' %s %s 86400.0 %s %s''' % (ltf_analyze_one_day_script_path, date.date(),
                                                      args.config.config_file, outdir))
        
        else:

            cmd_line = ("qsub -j oe -o %s -F '%s 86400.0 %s %s' %s" % (logfile_path,
                                                                           date.date(), args.config.config_file, outdir,
                                                                           ltf_analyze_one_day_script_path))

        print("\nSubmitting job %i:" % (i+1))
        print(cmd_line)

        if not args.simulate:

            subprocess.check_call(cmd_line,shell=True)

        else:

            print("(simulation is on, no job submitted)")

    if not args.simulate:

        print("\n\nSubmitted %i jobs" % (i+1))

    else:

        print("\n\nWould have submitted %i jobs" % (i+1))