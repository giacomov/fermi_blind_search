#!/usr/bin/env python

import argparse
import os
import subprocess
import astropy.io.fits as pyfits
import shutil

from fermi_blind_search.configuration import get_config
from fermi_blind_search.which import which

# What needs to happen in this script
# 1. call mdcget on the time interval it gets
# 2. check the counts of the returned data with the counts from the db
# 3. if the counts don't line up, rerun the analysis, else terminate
#   3a. call ltf_search_for_transient with a manual entry to the fit finals
# 4. analyze results and send email

def check_new_data(data_path, met_start, met_stop, counts):
    # make the directory to store the data from mdcget
    try:
        os.mkdirs(data_path)
    except:
        print("Could not make the directory %s" % data_path)
        raise

    # get the path to execute mdcget.py
    mdcget_path = which("mdcget.py")

    mdcget_cmd_line = ('%s --met_start %s --met_stop %s --outroot %s' % (mdcget_path, met_start, met_stop,
                                                                  data_path + "/data"))

    # call mdcget.py and wait for it to complete
    subprocess.check_call(mdcget_cmd_line, shell=True)

    # read the ft1 file to get the number of counts
    ft1_data = pyfits.getdata(data_path + "/data_ft1.fit", "EVENTS")
    new_counts = len(ft1_data)

    # return True if there is new data, False if there is not
    return new_counts > counts


def run_ltf_search(analysis_path):
    # make a directory to work in
    try:
        os.mkdirs(analysis_path + "/work")
    except:
        print("Could not make the directory %s" % analysis_path + "/tmp")
        raise

    # get the path to executre ltf_search_for_transients.py
    ltf_search_for_transients_path = which("ltf_search_for_transeints.py")

    ltf_search_cmd_line = ('%s --inp_fts %s --config %s --outfile %s --logfile %s --workdir %s' %
                           (ltf_search_for_transients_path,
                            ",".join([data_path + "/data_ft1.fit", data_path + "/data_ft2.fit"]),
                            configuration.config_file,
                            analysis_path + "/out.txt",
                            analysis_path + "/log.txt",
                            analysis_path + "/work"))
    subprocess.check_call(ltf_search_cmd_line, shell=True)

    # once the analysis has finished running, we remove the working directory
    try:
        shutil.rmtree(analysis_path + "/work")
    except:
        print("could not remove work directory %s" % analysis_path + "/work")
        raise
    return


def process_results():
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--met_start', help='Start time of the analysis', type=float, required=True)
    parser.add_argument('--duration', help='duration of the analysis', type=float, required=True)
    parser.add_argument('--counts', help='the counts used in the previous version of the analysis', type=int,
                        required=True)
    parser.add_argument('--outfile', help='Path to the outfile', type=str, required=True)
    parser.add_argument('--logfile', help='Path to the logfile', type=str, required=True)
    parser.add_argument('--config', help='Path to config file', type=get_config, required=True)

    args = parser.parse_args()

    # get the configuration object
    configuration = args.config

    # get the base path
    base_path = configuration.get("Real time", "base_path")

    # get the start and duration
    met_start = args.met_start
    duration = args.duration

    # calculate met_stop
    met_stop = met_start + duration

    # get the directory for this analysis
    analysis_path = os.path.abspath(os.path.expandvars(os.path.expanduser(base_path + "/" + str(met_start) + "_" +
                                                                          str(duration))))
    # if the directory does not exist, create it
    if not os.path.exists(analysis_path):
        try:
            os.mkdirs(analysis_path)
        except:
            print("Could not make the directory %s" % analysis_path)
            raise

    # directory we will use to store data from mdcget.py
    data_path = analysis_path + "/data"

    if check_new_data(data_path, met_start, met_stop, args.counts):
        # there is new data! so we rerun the analysis
        run_ltf_search(analysis_path)
        process_results()







