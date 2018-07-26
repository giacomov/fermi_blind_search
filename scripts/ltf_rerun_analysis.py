#!/usr/bin/env python

#PBS -l walltime=04:00:00
#PBS -l nodes=1:ppn=10
#PBS -l vmem=30gb
#PBS -V

import argparse
import os
import subprocess
import astropy.io.fits as pyfits
import shutil

from fermi_blind_search.configuration import get_config
from fermi_blind_search.which import which
from fermi_blind_search.database import Database


def make_dir_if_not_exist(path):

    # check if the directory already exists
    if not os.path.exists(path):
        # it doesn't! so we try to make it
        try:
            os.makedirs(path)
        except:
            print("Could not make the directory %s" % path)
            raise
        else:
            print("successfully created dir %s" % path)


def check_new_data(met_start, met_stop, counts, ssh_host, source_path):

    # get the path to execute mdcget.py
    # mdcget_path = which("mdcget.py")
    #
    # # command to get the files that would be used in this analysis
    # mdcget_cmd_line = ('%s --met_start %s --met_stop %s --type FT1' % (mdcget_path, met_start, met_stop))
    #
    # print(mdcget_cmd_line)
    #
    # # call mdcget.py, wait for it to complete, and get its output
    # p = subprocess.Popen(mdcget_cmd_line, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # out, err = p.communicate()
    #
    # # split the string of files output on \n
    # # TODO: add condition to ensure that at least 1 file is returned
    # ft1_files = out.split("\n")
    #
    # new_counts = 0
    # for i in range(len(ft1_files) - 1):
    #     # open the fit file
    #     ft1_data = pyfits.getdata(ft1_files[i], "EVENTS")
    #
    #     # get the counts that occured within the time interval of interest
    #     idx = (ft1_data.field("TIME") >= met_start) & (ft1_data.field("TIME") < met_stop)
    #
    #     # add this to the total number of counts
    #     new_counts += np.sum(idx)

    try:
        out = subprocess.check_output(
            "ssh %s 'source %s ; mdcget.py --met_start %s --met_stop %s --count'" % (ssh_host, source_path, met_start, met_stop), shell=True)
    except:
        raise IOError("Could not get number of counts between %s and %s" % (met_start, met_stop))

    number_of_counts = int(out.split()[-1])

    print(number_of_counts)

    # return True if there is new data, False if there is not
    return number_of_counts > counts


def get_data(data_path, met_start, met_stop, config):

    # make directory to store the data
    make_dir_if_not_exist(data_path)

    # get the path to execute mdcget.py
    mdcget_path = which("mdcget.py")

    mdcget_cmd_line = ('%s --met_start %s --met_stop %s --outroot %s' % (mdcget_path, met_start, met_stop,
                                                                         os.path.join(data_path, "data")))

    print(mdcget_cmd_line)

    # call mdcget and wait for it to return
    subprocess.check_call(mdcget_cmd_line, shell=True)

    # get the counts from this call just in case new data has arrive between the last call to mdcget
    ft1_data = pyfits.getdata(os.path.join(data_path, "data_ft1.fit"), "EVENTS")

    # update the counts stored in the database
    print("Updating Database")
    counts = len(ft1_data)
    db = Database(config)
    db.update_analysis_counts(met_start, float(met_stop) - float(met_start), counts)

    return


def run_ltf_search(analysis_path, data_path):

    # make a work directory
    workdir = os.path.join(analysis_path, "work")
    make_dir_if_not_exist(workdir)

    # store current directory
    cwd = os.getcwd()

    # move there
    os.chdir(workdir)

    # get the path to execute ltf_search_for_transients.py
    ltf_search_for_transients_path = which("ltf_search_for_transients.py")

    fit_file_path = ",".join([os.path.join(data_path, "data_ft1.fit"), os.path.join(data_path, "data_ft2.fit")])
    print(fit_file_path)
    ltf_search_cmd_line = ('%s --inp_fts %s --config %s --outfile %s --logfile %s --workdir %s' %
                           (ltf_search_for_transients_path,
                            fit_file_path,
                            configuration.config_file,
                            os.path.join(analysis_path, "out.txt"),
                            os.path.join(analysis_path,  "log.txt"), workdir))
    print(ltf_search_cmd_line)

    try:
        # call ltf_seach_for_transients
        subprocess.check_call(ltf_search_cmd_line, shell=True)

    except:
        raise

    finally:
        # move back to original directory
        os.chdir(cwd)

        try:
            # remove working directory
            shutil.rmtree(workdir)
        except:
            print("Could not remove directory: %s" % workdir)

    return


def process_results(analysis_path, config_path):

    # get path to ltf_send_results_email
    results_path = which("ltf_process_search_results.py")

    # format the command
    send_results_cmd_line = ("%s --results %s --config %s" % (results_path, analysis_path + "/out.txt", config_path))
    print(send_results_cmd_line)

    # execute
    subprocess.check_call(send_results_cmd_line, shell=True)


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
    make_dir_if_not_exist(analysis_path)

    # directory we will use to store data from mdcget.py
    data_path = os.path.join(analysis_path, "data")

    print("data path: %s" % data_path)
    print("starting counts check")

    # make a directory to store data from mcdget (if we fetch data)
    make_dir_if_not_exist(data_path)

    ssh_host = configuration.get("Remote access", "ssh_host")
    source_path = configuration.get("Remote access", "source_path")

    if check_new_data(met_start, met_stop, args.counts, ssh_host, source_path):
        # there is new data! so we rerun the analysis
        print("We need to rerun the analysis, fetching data...")
        # first actually fetch the data we will use as a single file
        get_data(data_path, met_start, met_stop, configuration)
        print("finished getting data, about to start search")

        # run ltf_search_for_transients
        run_ltf_search(analysis_path, data_path)

        # check results against candidates we have already found and send emails
        process_results(analysis_path, configuration.config_file)

    # clean up data directory
    try:
        shutil.rmtree(data_path)
    except:
        print("Could not remove data directory %s " % data_path)
        raise
