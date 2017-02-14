#!/usr/bin/env python

"""This is a global script that takes actual or simulated Fermi data and searches it for transients.
    Actual data is specified by a date, simulated is given by a specific ft1 and ft2 file"""

import argparse

import os
from astropy.io import fits

from fermi_blind_search.execute_command import execute_command

# execute only if run from command line
if __name__ == "__main__":

    # create parser for this script
    parser = argparse.ArgumentParser('Search input data for Transients')

    # add the arguments needed to the parser

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--date', help='date specifying file to load')
    group.add_argument('--inp_fts', help='filenames of ft1 and ft2 input, separated by a comma (ex: foo.ft1,bar.ft2)')

    parser.add_argument("--irf", help="Instrument response function name to be used", type=str,
                        required=True)
    parser.add_argument("--probability", help="Probability of null hypothesis", type=float, default=1e-5)
    parser.add_argument("--min_dist", help="Distance above which regions are not considered to overlap", type=float,
                        required=True)
    parser.add_argument("--out_file", help="Name of text file containing list of possible transients", type=str,
                        required=True)

    # optional
    parser.add_argument("--duration", help="Duration of analysis in seconds (default: 86400)", default=86400)
    parser.add_argument("--config_file",
                        help="Name of configuration file (use this, or set the LTF_CONFIG_FILE variable",
                        default=None, required=False)
    parser.add_argument("--loglevel", help="Level of log detail (DEBUG, INFO)", default='info')
    parser.add_argument("--logfile", help="Name of logfile for the ltfsearch.py script", default='ltfsearch.log')
    parser.add_argument("--workdir", help="Path of work directory", default=os.getcwd())

    # (The Zenith cut is defined in the configuration.txt file of ltfsearch)

    # parser.add_argument("--zmax", help="Maximum zenith allowed for data to be considered", required=True, type=float)

    # parse the arguments
    args = parser.parse_args()

    if args.config_file is not None:

        os.environ["LTF_CONFIG_FILE"] = args.config_file

    temp_file = 'active_file.txt'

    # if using real data

    if args.date:

        # bayesian blocks

        cmd_line = 'ltfsearch.py --date %s --duration 86400.0 --irfs %s --probability %s --loglevel %s --logfile %s ' \
                   '--workdir %s --outfile %s' % (args.date, args.irf, args.probability, args.loglevel, args.logfile,
                                                  args.workdir, temp_file)

        execute_command(cmd_line)

        # remove redundant triggers

        cmd_line = 'ltf_remove_redundant_triggers.py --in_list %s --min_dist %s --out_list %s' % (temp_file,
                                                                                                  args.min_dist,
                                                                                                  args.out_file)

        execute_command(cmd_line)

    # else using simulated data
    else:

        # get names of ft1 and ft2 files
        ft1_name = os.path.abspath(os.path.expandvars(os.path.expanduser(args.inp_fts.rsplit(",", 1)[0])))
        ft2_name = os.path.abspath(os.path.expandvars(os.path.expanduser(args.inp_fts.rsplit(",", 1)[1])))

        with fits.open(str(ft1_name)) as ft1:

            sim_start = ft1[0].header['TSTART']
            sim_end = ft1[0].header['TSTOP']

        dur = sim_end - sim_start

        # bayesian blocks

        cmd_line = 'ltfsearch.py --date %s --duration %s --irfs %s --probability %s --loglevel %s --logfile %s ' \
                   '--workdir %s --outfile %s --ft1 %s --ft2 %s' % (sim_start, dur, args.irf, args.probability,
                                                                    args.loglevel, args.logfile, args.workdir,
                                                                    temp_file, ft1_name, ft2_name)

        execute_command(cmd_line)

        # remove redundant triggers

        cmd_line = 'ltf_remove_redundant_triggers.py.py --in_list active_file.txt ' \
                   '--min_dist %s --out_list %s' %(args.min_dist, args.out_file)

        execute_command(cmd_line)

    os.remove(temp_file)

    print "\nSearch complete. Results in %s" % args.out_file
