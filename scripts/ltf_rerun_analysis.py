#!/usr/bin/env python

import argparse
import os
import subprocess
import astropy.io.fits as pyfits
import shutil
import numpy as np

from fermi_blind_search.configuration import get_config
from fermi_blind_search.which import which

# What needs to happen in this script
# 1. call mdcget on the time interval it gets
# 2. check the counts of the returned data with the counts from the db
# 3. if the counts don't line up, rerun the analysis, else terminate
#   3a. call ltf_search_for_transient with a manual entry to the fit finals
# 4. analyze results and send email


def make_dir_if_not_exist(path):
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except:
            print("Could not make the directory %s" % path)
            raise


def check_new_data(met_start, met_stop, counts):
    # make the directory to store the data from mdcget
    # try:
    #     os.makedirs(data_path)
    # except:
    #     print("Could not make the directory %s" % data_path)
    #     raise

    make_dir_if_not_exist(data_path)

    # get the path to execute mdcget.py
    mdcget_path = which("mdcget.py")
    #
    # mdcget_cmd_line = ('%s --met_start %s --met_stop %s --outroot %s' % (mdcget_path, met_start, met_stop,
    #                                                               data_path + "/data"))

    # command to get the files that would be used in this analysis
    mdcget_cmd_line = ('%s --met_start %s --met_stop %s --type FT1' % (mdcget_path, met_start, met_stop))

    # call mdcget.py, wait for it to complete, and get its output
    p = subprocess.Popen(mdcget_cmd_line, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()

    # split the string of files output on \n
    # TODO: add condition to ensure that at least 1 file is returned
    ft1_files = out.split("\n")

    new_counts = 0
    for i in range(len(ft1_files) -1):
        # open the fit file
        ft1_data = pyfits.getdata(ft1_files[i], "EVENTS")

        # get the counts that occured within the time interval of interest
        idx = (ft1_data.field("TIME") >= met_start) & (ft1_data.field("TIME") < met_stop)

        # add this to the total number of counts
        new_counts += np.sum(idx)

    print(new_counts)

    # return True if there is new data, False if there is not
    return new_counts > counts


def get_data(data_path, met_start, met_stop):

    # make directory to store the data
    make_dir_if_not_exist(data_path)

    # get the path to execute mdcget.py
    mdcget_path = which("mdcget.py")

    mdcget_cmd_line = ('%s --met_start %s --met_stop %s --outroot %s' % (mdcget_path, met_start, met_stop,
                                                                         data_path + "/data"))

    # call mdcget and wait for it to return
    subprocess.check_call(mdcget_cmd_line, shell=True)

    return


def run_ltf_search(analysis_path):
    # make a directory to work in
    # try:
    #     os.makedirs(analysis_path + "/work")
    # except:
    #     print("Could not make the directory %s" % analysis_path + "/tmp")
    #     raise
    make_dir_if_not_exist(analysis_path + "/work")

    # get the path to execute ltf_search_for_transients.py
    ltf_search_for_transients_path = which("ltf_search_for_transients.py")

    ltf_search_cmd_line = ('%s --inp_fts %s --config %s --outfile %s --logfile %s --workdir %s' %
                           (ltf_search_for_transients_path,
                            ",".join([data_path + "/data_ft1.fit", data_path + "/data_ft2.fit"]),
                            configuration.config_file,
                            analysis_path + "/out.txt",
                            analysis_path + "/log.txt",
                            analysis_path + "/work"))
    subprocess.check_call(ltf_search_cmd_line, shell=True)
    print("ltf_search complete")

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
    print("Base Path: %s" % base_path)

    # get the start and duration
    met_start = args.met_start
    duration = args.duration

    # calculate met_stop
    met_stop = met_start + duration

    # get the directory for this analysis
    analysis_path = os.path.abspath(os.path.expandvars(os.path.expanduser(base_path + "/" + str(met_start) + "_" +
                                                                          str(duration))))
    print("analysis path: %s" % analysis_path)
    # if the directory does not exist, create it
    # if not os.path.exists(analysis_path):
    #     try:
    #         os.makedirs(analysis_path)
    #     except:
    #         print("Could not make the directory %s" % analysis_path)
    #         raise
    make_dir_if_not_exist(analysis_path)

    # directory we will use to store data from mdcget.py
    data_path = analysis_path + "/data"

    print("data path: %s" % data_path)
    print("starting counts check")

    if check_new_data(met_start, met_stop, args.counts):
        # there is new data! so we rerun the analysis
        print("We made it!!!")
        get_data(data_path, met_start, met_stop)
        # run_ltf_search(analysis_path)
        # process_results()







