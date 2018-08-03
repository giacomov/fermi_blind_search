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
from fermi_blind_search.send_email import send_email


def check_new_data(met_start, met_stop, counts, ssh_host, config, logger):

    logger.info("Checking if there is new data for the analysis with the parameters: met_start: %s met_stop: %s, "
               "counts: %s" % (met_start, met_stop, counts))

    try:
        # call mdcget with --count to just return the counts in the time range
        out = subprocess.check_output(
            "ssh %s 'mdcget.py --met_start %s --met_stop %s --count'" % (ssh_host, met_start, met_stop), shell=True)
    except:
        raise IOError("Could not get number of counts between %s and %s" % (met_start, met_stop))

    number_of_counts = int(out.split()[-1])

    if number_of_counts > counts:

        logger.info("Updating the database to reflect the new number of counts. The parameters are: met_start %s, "
                    "duration: %s, counts %s" % (met_start, float(met_stop) - float(met_start), number_of_counts))
        with database_connection(configuration):
            """
            With the current configuration of the real time search, tunneling is handled using an autossh connection
            established when a job is started on the farm. So database_connection just returns a plain database connection
            with no tunneling. To open a connection with tunneling, see the context manager in database.py and set up your
            configuration file accordingly  
            """
            db = Database(config)
            db.update_analysis_counts(met_start, float(met_stop) - float(met_start), number_of_counts)
    else:

        logger.info("Number of counts from mdcget was %s, which is the same as in the database (%s), not updating the "
                    "database")

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
    parser.add_argument('--directory', help='Path to the directory', type=str, required=True)
    parser.add_argument('--config', help='Path to config file', type=get_config, required=True)
    parser.add_argument('--debug', help='Activate debugging messages', action='store_true', default=False)

    args = parser.parse_args()

    # set up logging
    logger = myLogging.log.getLogger("ltf_rerun_analysis")

    if args.debug:

        myLogging.set_level("DEBUG")

    else:

        myLogging.set_level("INFO")

    logger.debug("Arguments: %s" % (args.__dict__))

    # get the configuration object
    configuration = args.config

    # get the start and duration
    met_start = args.met_start
    duration = args.duration

    # calculate met_stop
    met_stop = met_start + duration

    # get the directory for this analysis
    analysis_path = args.directory

    logger.info("Results and log files for this analysis will be stored at %s" % analysis_path)

    # if the directory does not exist, create it
    make_dir_if_not_exist(analysis_path)

    # directory we will use to store data from mdcget.py
    unique_id = 0
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

        unique_id = "Analysis not running on farm"

        logger.info("The at_slac value in the configuration file is not True or False, so we don't know if we are at "
                    "Stanford or SLAC, please change the configuration value. In the meantime, the work directory will "
                    "be set to: %s" % workdir)

    logger.info("Making the work directory and setting up paths for out and log files")

    # make a directory to store data from mcdget (if we fetch data)
    make_dir_if_not_exist(workdir)
    outfile = os.path.join(workdir, "out.txt")
    logfile = os.path.join(workdir, "log.txt")

    # store where we are now, so we can return
    cwd = os.getcwd()

    # move into the work directory
    os.chdir(workdir)

    ssh_host = configuration.get("Remote access", "ssh_host")

    logger.info("Checking if the counts of the analysis have changed")

    if check_new_data(met_start, met_stop, args.counts, ssh_host, configuration, logger):
        # there is new data! so we rerun the analysis (and send an email)

        logger.info("There is new data for this analysis so we continue with the analysis")

        # send an email to alert that a new analysis is being run
        host = configuration.get("Email", "host")
        port = configuration.get("Email", "port")
        username = configuration.get("Email", "username")
        recipients = configuration.get("Email", "recipient")
        subject = "ltf_rerun_analysis.py STARTING"
        email_string = ("Starting a new analysis with the following parameters: \n met_start: %s \n met_stop: %s \n "
                        "jobID: %s" % (met_start, met_stop, unique_id))

        # if we need to open an ssh tunnel to send the email (see send_email() in send_email.py) set up the ssh_tunnel
        # here and send tunnel=ssh_tunnel to send_email
        logger.info("Email parameters: host: %s, port %s, username: %s" % (host, port, username))
        send_email(host, port, username, email_string, recipients, subject)

        try:

            with database_connection(configuration):
                """
                With the current configuration of the real time search, tunneling is handled using an autossh connection
                established when a job is started on the farm. So database_connection just returns a plain database connection
                with no tunneling. To open a connection with tunneling, see the context manager in database.py and set up your
                configuration file accordingly  
                """
                logger.info("Database connection established")

                # first actually fetch the data we will use as a single file
                get_data(workdir, met_start, met_stop, configuration, logger)

                # run ltf_search_for_transients
                run_ltf_search(workdir, outfile, logfile, logger)

                # if we make it this far, the analysis has been successful and we want to copy the results back
                # we do this here so that if process_results fails, we still have the results files where we want them
                shutil.copy2(outfile, analysis_path)
                shutil.copy2(logfile, analysis_path)

                # check results against candidates we have already found and send emails
                process_results(outfile, configuration.config_file, logger)

        except:

            traceback.print_exc(sys.stdout)
            error_msg = traceback.format_exc()

            # send an email to alert that the analysis has failed
            host = configuration.get("Email", "host")
            port = configuration.get("Email", "port")
            username = configuration.get("Email", "username")
            recipients = configuration.get("Email", "recipient")
            subject = "ltf_rerun_analysis.py ERROR"

            # if we need to open an ssh tunnel to send the email (see send_email() in send_email.py) set up the
            # ssh_tunnel here and send tunnel=ssh_tunnel to send_email

            send_email(host, port, username, error_msg, recipients, subject)

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
