#!/usr/bin/env python

#PBS -l walltime=04:00:00
#PBS -l vmem=30gb

import argparse
import os
import subprocess
import astropy.io.fits as pyfits
import shutil
import traceback
import sys


from fermi_blind_search.configuration import get_config
from fermi_blind_search.which import which
from fermi_blind_search.database import Database, database_connection
from fermi_blind_search.make_directory import make_dir_if_not_exist
from fermi_blind_search import myLogging



def check_new_data(met_start, met_stop, counts, ssh_host, logger):

    logger.info("Checking if there is new data for the analysis with the parameters: met_start: %s met_stop: %s, "
               "counts: %s" % (met_start, met_stop, counts))

    try:
        # call mdcget with --count to just return the counts in the time range
        out = subprocess.check_output(
            "ssh %s 'mdcget.py --met_start %s --met_stop %s --count'" % (ssh_host, met_start, met_stop), shell=True)
    except:
        raise IOError("Could not get number of counts between %s and %s" % (met_start, met_stop))

    number_of_counts = int(out.split()[-1])

    # return True if there is new data, False if there is not
    return number_of_counts > counts


def get_data(data_path, met_start, met_stop, config, logger):

    logger.info("Fetching data for the analysis with the parameters: met_start: %s met_stop: %s, " % (met_start,
                                                                                                     met_stop))
    # make directory to store the data
    make_dir_if_not_exist(data_path)

    # get the path to execute mdcget.py
    mdcget_path = which("mdcget.py")

    mdcget_cmd_line = ('%s --met_start %s --met_stop %s --outroot %s' % (mdcget_path, met_start, met_stop,
                                                                         os.path.join(data_path, "data")))

    logger.info("mdcget command line: %s" % mdcget_cmd_line)

    # call mdcget and wait for it to return
    subprocess.check_call(mdcget_cmd_line, shell=True)

    # get the counts from this call just in case new data has arrive between the last call to mdcget
    ft1_data = pyfits.getdata(os.path.join(data_path, "data_ft1.fit"), "EVENTS")

    # update the counts stored in the database
    counts = len(ft1_data)
    logger.info("Updating the database to reflect the new number of counts. The parameters are: met_start %s, "
                "duration: %s, counts %s" % (met_start, float(met_stop) - float(met_start), counts))
    db = Database(config)
    db.update_analysis_counts(met_start, float(met_stop) - float(met_start), counts)

    return


def run_ltf_search(workdir, outfile, logfile, logger):

    # get the path to execute ltf_search_for_transients.py
    ltf_search_for_transients_path = which("ltf_search_for_transients.py")

    fit_file_path = ",".join([os.path.join(workdir, "data_ft1.fit"), os.path.join(workdir, "data_ft2.fit")])

    logger.info("Running ltf_search_for_transients with data stored at: %s" % fit_file_path)

    ltf_search_cmd_line = ('%s --inp_fts %s --config %s --outfile %s --logfile %s --workdir %s' %
                           (ltf_search_for_transients_path,
                            fit_file_path, configuration.config_file, outfile, logfile, workdir))

    logger.info("ltf_search_for_transients command line: %s" % ltf_search_cmd_line)


    try:
        # call ltf_seach_for_transients
        subprocess.check_call(ltf_search_cmd_line, shell=True)

    except:
        raise

    return


def process_results(outfile, config_path, logger):

    logger.info("Processing results stored at %s" % outfile)
    # get path to ltf_send_results_email
    results_path = which("ltf_process_search_results.py")

    # format the command
    send_results_cmd_line = ("%s --results %s --config %s" % (results_path, outfile, config_path))

    logger.info("process results command line: %s" % send_results_cmd_line)

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
    parser.add_argument('--debug', help='Activate debugging messages', action='store_true', default=False)

    args = parser.parse_args()

    # set up logging
    logger = myLogging.log.getLogger("ltf_rerun_analysis")

    if args.debug:

        myLogging.setLevel("DEBUG")

    else:

        myLogging.setLevel("INFO")

    logger.debug("Arguments: %s" % (args.__dict__))

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

    logger.info("Results and log files for this analysis will be stored at %s" % analysis_path)

    # if the directory does not exist, create it
    make_dir_if_not_exist(analysis_path)

    # directory we will use to store data from mdcget.py
    at_slac = configuration.get("Remote access", "at_slac")
    if at_slac == "True":
        unique_id = os.environ.get("LSB_JOBID")

        workdir = os.path.join('/scratch', unique_id)

        logger.info("We are at SLAC, the work directory is: %s" % workdir)
    elif at_slac == "False":
        unique_id = os.environ.get("PBS_JOBID").split(".")[0]

        # os.path.join joins two path in a system-independent way
        workdir = os.path.join('/dev/shm', unique_id)

        logger.info("We are at Stanford, the work directory is: %s" % workdir)
    else:
        workdir = os.path.join(analysis_path, "data")

        logger.info("The at_slac value in the configuration file is not True or False, so we don't know if we are at "
                    "Stanford or SLAC, please change the configuration value. In the meantime, the work directory will "
                    "be set to: %s" % workdir)

    logger.info("Making the work directory and setting up paths for out and log files")

    # make a directory to store data from mcdget (if we fetch data)
    make_dir_if_not_exist(workdir)
    outfile = os.path.join(workdir, args.outfile)
    logfile = os.path.join(workdir, args.logfile)

    # store where we are now, so we can return
    cwd = os.getcwd()

    # move into the work directory
    os.chdir(workdir)

    ssh_host = configuration.get("Remote access", "ssh_host")

    logger.info("Checking if the counts of the analysis have changed")

    if check_new_data(met_start, met_stop, args.counts, ssh_host, logger):
        logger.info("There is new data for this analysis so we continue with the analysis")

        try:

            with database_connection(configuration):
                logger.info("Database connection established")
                # there is new data! so we rerun the analysis

                # first actually fetch the data we will use as a single file
                get_data(workdir, met_start, met_stop, configuration, logger)

                # run ltf_search_for_transients
                run_ltf_search(workdir, outfile, logfile, logger)

                # check results against candidates we have already found and send emails
                process_results(outfile, configuration.config_file, logger)

        except:

            traceback.print_exc(sys.stdout)

        else:

            shutil.copy2(outfile, analysis_path)
            shutil.copy2(logfile, analysis_path)

        finally:
            # move back to where we were
            os.chdir(cwd)

            # clean up data directory
            try:
                shutil.rmtree(workdir)
            except:
                logger.error("Could not remove data directory %s " % workdir)
                raise
    else:
        logger.info("There is no new data for this analysis, ending the analysis now")
        # move back to where we were
        os.chdir(cwd)

        # clean up data directory
        try:
            shutil.rmtree(workdir)
        except:
            logger.error("Could not remove data directory %s " % workdir)
            raise
