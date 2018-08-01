#!/usr/bin/env python

import argparse
import subprocess
import os
import sys
import traceback


from fermi_blind_search.configuration import get_config
from fermi_blind_search.database import Database, database_connection
from fermi_blind_search.which import which
from myDataCatalog import DB
from fermi_blind_search.make_directory import make_dir_if_not_exist
from fermi_blind_search import myLogging
from fermi_blind_search.send_email import send_email


def rerun_analysis(rerun_analysis_path, met_start, duration, counts, outfile, logfile, config, logger):

    logger.info("Running an analysis with the following parameters: met_start: %s, duration: %s counts %s "
                "outfile: %s logfile: %s" % (met_start, duration, counts, outfile, logfile))

    base_path = os.path.abspath(os.path.expandvars(
        os.path.expanduser(config.get("Real time", "base_path"))))
    log_path = os.path.join(base_path, str(met_start) + "_" + str(float(duration)))
    make_dir_if_not_exist(log_path)
    log_path = os.path.join(log_path, str(met_start) + "_" + str(float(duration)) + "_farm_log.txt")

    # format the command we will execute
    rerun_analysis_cmd_line = config.get("Real time", "farm_command")
    rerun_analysis_cmd_line = rerun_analysis_cmd_line.replace("$FARM_LOG_PATH", log_path)
    # the -N parameter of the qsub command only accepts strings of 15 chars or less
    rerun_analysis_cmd_line = rerun_analysis_cmd_line.replace("$JOB_NAME",
                                                              "%.15s" % str(met_start) + "_" + str(float(duration)))
    rerun_analysis_cmd_line = rerun_analysis_cmd_line.replace("$NUM_CPUS", config.get("Hardware", "ncpus"))
    rerun_analysis_cmd_line = rerun_analysis_cmd_line.replace("$MET_START", str(met_start))
    rerun_analysis_cmd_line = rerun_analysis_cmd_line.replace("$DURATION", str(duration))
    rerun_analysis_cmd_line = rerun_analysis_cmd_line.replace("$COUNTS", str(counts))
    rerun_analysis_cmd_line = rerun_analysis_cmd_line.replace("$OUTFILE", str(outfile))
    rerun_analysis_cmd_line = rerun_analysis_cmd_line.replace("$LOGFILE", str(logfile))
    rerun_analysis_cmd_line = rerun_analysis_cmd_line.replace("$CONFIG", str(config.config_file))
    rerun_analysis_cmd_line = rerun_analysis_cmd_line.replace("$SCRIPT", rerun_analysis_path)

    # if you want to run locally, use this command line
    # rerun_analysis_cmd_line = ("%s --met_start %s --duration %s --counts %s --outfile %s --logfile %s --config %s" %
    #                            (rerun_analysis_path, met_start, duration, counts, outfile, logfile,
    #                             config.config_file))

    logger.info("Starting a job on the farm with the command: \n %s" % rerun_analysis_cmd_line)

    # execute ltf_rerun_analysis.py
    subprocess.check_call(rerun_analysis_cmd_line, shell=True)


def run_real_time_analysis(most_recent_event_time, start_rerun_interval, end_rerun_interval, configuration, logger):

    # start a connection with the database storing analysis and transient candidates
    with database_connection(configuration):
        logger.debug("Connection to the database established")
        real_time_db = Database(configuration)

        # fetch all analyses that were run using data from the interval we wish to rerun
        # subtract an extra 1 from the second time bc get_analysis_between_times is inclusive, and we separately run
        # analysis of the the analysis from most_recent_event_time - end_rerun_interval to most_recent_event_time
        logger.info("Fetching all analyses that were run using data from %s to %s" %
                    (most_recent_event_time - start_rerun_interval, most_recent_event_time - end_rerun_interval - 1))
        analyses_to_run = real_time_db.get_analysis_between_times(most_recent_event_time - start_rerun_interval,
                                                                  most_recent_event_time - end_rerun_interval - 1)

        logger.debug("Successfully fetched the analyses to rerun")

        # get the path to ltf_rerun_analysis.py
        rerun_analysis_path = which("ltf_rerun_analysis.py")

        for row in analyses_to_run:
            # start a job on the farm that runs ltf_rerun_analysis.py
            rerun_analysis(rerun_analysis_path, row.met_start, row.duration, row.counts, row.outfile,
                           row.logfile, configuration, logger)

        logger.info("Finished reruning past analyses, getting the most recent analysis. Query parameters are "
                    "met_start: %s, met_stop: %s" % (most_recent_event_time - end_rerun_interval,
                                                     most_recent_event_time))
        # run an analysis from most_recent_event_time - end_rerun_interval to most_recent_event

        # check if the same analysis has already been run
        most_recent_analysis = real_time_db.get_exact_analysis(most_recent_event_time - end_rerun_interval,
                                                               most_recent_event_time)
        logger.debug("Successfully fetched the most recent analysis")
        if len(most_recent_analysis) == 0:
            # this analysis will be run for the first time
            logger.info("The analysis of the most recent data has not been run before, we will run it for the first "
                        "time")

            # add the analysis to the database with 0 as counts (will be replaced when the analysis is actually run)
            logger.info("Adding the new analysis to the database with the parameters: met_start: %s, duration: %s, "
                        "counts: %s, outfile: %s, logfile: %s" % (most_recent_event_time - end_rerun_interval,
                                                                  end_rerun_interval, 0, "out.txt", "log.txt"))

            analysis_vals = {'met_start': most_recent_event_time - end_rerun_interval, 'duration': end_rerun_interval,
                             'counts': 0, 'outfile': "out.txt", 'logfile': "log.txt"}
            real_time_db.add_analysis(analysis_vals)

            logger.debug("Successfully added analysis to database")

            # run the analysis
            rerun_analysis(rerun_analysis_path, most_recent_event_time - end_rerun_interval, end_rerun_interval, 0,
                           "out.txt", "log.txt", configuration, logger)
        else:
            # TODO: Add check that there is only one results returned??
            # this analysis has been run before so we want to rerun it with the same parameters
            logger.info("The analysis of the most recent data has been run before, we will rerun it.")
            row = most_recent_analysis[0]
            rerun_analysis(rerun_analysis_path, row.met_start, row.duration, row.counts, row.outfile, row.logfile,
                           configuration, logger)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='Path to config file', type=get_config, required=True)
    parser.add_argument('--test_time', help='For testing purposes. Sets the most_recent_event_time instead of selecting'
                                            'the time of the most recent recorded event', type=float, required=False)
    parser.add_argument('--debug', help='Activate debugging messages', action='store_true', default=False)

    args = parser.parse_args()

    # set up logging
    logger = myLogging.log.getLogger("ltf_real_time.py")

    if args.debug:

        myLogging.set_level("DEBUG")

    else:

        myLogging.set_level("INFO")

    logger.debug("Arguments: %s" % (args.__dict__))

    configuration = args.config

    # TODO: remove this later, testing the email functionality
    host = configuration.get("Email", "host")
    port = configuration.get("Email", "port")
    username = configuration.get("Email", "username")
    email_string = "ltf_real_time.py has started"
    recipients = configuration.get("Email", "recipient")
    subject = configuration.get("Email", "subject")
    ssh_tunnel = (configuration.get("Email", "ssh_tunnel_host"),
                  configuration.get("Email", "ssh_tunnel_port"),
                  configuration.get("Email", "ssh_tunnel_username"),
                  configuration.get("Email", "ssh_tunnel_key_directory"))
    send_email(host, port, username, email_string, recipients, subject, tunnel=ssh_tunnel)

    # get the interval to rerun analyses over and convert them to seconds
    start_rerun_interval = int(configuration.get("Real time", "start_interval")) * 3600
    end_rerun_interval = int(configuration.get("Real time", "end_interval")) * 3600

    if args.test_time is None:
        # get the time of the most recent event
        logger.info("Getting the time of the most recent event")
        event_db = DB.DB()
        c = event_db.query(''' select max(MET_stop) from FT1''')
        most_recent_event_time = c.fetchall()[0][0]
        logger.info("Most recent event time: %s" % most_recent_event_time)
    else:
        # we want to run the script as if this is the most recent event time
        most_recent_event_time = args.test_time
        logger.info("We are running the search as if %s is the time of the most recent event" % most_recent_event_time)

    try:
        run_real_time_analysis(most_recent_event_time, start_rerun_interval, end_rerun_interval, configuration, logger)
    except:
        # an error has occured, so we want to send an email
        error_msg = traceback.format_exc()
        host = configuration.get("Email", "host")
        port = configuration.get("Email", "port")
        username = configuration.get("Email", "username")
        recipients = configuration.get("Email", "recipient")
        subject = "ltf_real_time.py ERROR"
        send_email(host, port, username, error_msg, recipients, subject)



    # # start a connection with the database storing analysis and transient candidates
    # with database_connection(configuration):
    #     logger.debug("Connection to the database established")
    #     real_time_db = Database(configuration)
    #
    #     # fetch all analyses that were run using data from the interval we wish to rerun
    #     # subtract an extra 1 from the second time bc get_analysis_between_times is inclusive, and we separately run
    #     # analysis of the the analysis from most_recent_event_time - end_rerun_interval to most_recent_event_time
    #     logger.info("Fetching all analyses that were run using data from %s to %s" %
    #                 (most_recent_event_time - start_rerun_interval, most_recent_event_time - end_rerun_interval - 1))
    #     analyses_to_run = real_time_db.get_analysis_between_times(most_recent_event_time - start_rerun_interval,
    #                                                               most_recent_event_time - end_rerun_interval - 1)
    #
    #     logger.debug("Successfully fetched the analyses to rerun")
    #
    #     # get the path to ltf_rerun_analysis.py
    #     rerun_analysis_path = which("ltf_rerun_analysis.py")
    #
    #     for row in analyses_to_run:
    #         # start a job on the farm that runs ltf_rerun_analysis.py
    #         rerun_analysis(rerun_analysis_path, row.met_start, row.duration, row.counts, row.outfile,
    #                        row.logfile, configuration, logger)
    #
    #     logger.info("Finished reruning past analyses, getting the most recent analysis. Query parameters are "
    #                 "met_start: %s, met_stop: %s" % (most_recent_event_time - end_rerun_interval,
    #                                                  most_recent_event_time))
    #     # run an analysis from most_recent_event_time - end_rerun_interval to most_recent_event
    #
    #     # check if the same analysis has already been run
    #     most_recent_analysis = real_time_db.get_exact_analysis(most_recent_event_time - end_rerun_interval,
    #                                                            most_recent_event_time)
    #     logger.debug("Successfully fetched the most recent analysis")
    #     if len(most_recent_analysis) == 0:
    #         # this analysis will be run for the first time
    #         logger.info("The analysis of the most recent data has not been run before, we will run it for the first "
    #                     "time")
    #
    #         # add the analysis to the database with 0 as counts (will be replaced when the analysis is actually run)
    #         logger.info("Adding the new analysis to the database with the parameters: met_start: %s, duration: %s, "
    #                     "counts: %s, outfile: %s, logfile: %s" % (most_recent_event_time - end_rerun_interval,
    #                                                               end_rerun_interval,0, "out.txt", "log.txt"))
    #
    #         analysis_vals = {'met_start': most_recent_event_time - end_rerun_interval, 'duration': end_rerun_interval,
    #                          'counts': 0, 'outfile': "out.txt", 'logfile': "log.txt"}
    #         real_time_db.add_analysis(analysis_vals)
    #
    #         logger.debug("Successfully added analysis to database")
    #
    #         # run the analysis
    #         rerun_analysis(rerun_analysis_path, most_recent_event_time - end_rerun_interval, end_rerun_interval, 0,
    #                        "out.txt", "log.txt", configuration, logger)
    #     else:
    #         # TODO: Add check that there is only one results returned??
    #         # this analysis has been run before so we want to rerun it with the same parameters
    #         logger.info("The analysis of the most recent data has been run before, we will rerun it.")
    #         row = most_recent_analysis[0]
    #         rerun_analysis(rerun_analysis_path, row.met_start, row.duration, row.counts, row.outfile, row.logfile,
    #                        configuration, logger)
