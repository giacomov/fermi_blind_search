#!/usr/bin/env python

import argparse
import subprocess

from fermi_blind_search.configuration import get_config
from fermi_blind_search.database import Database
from fermi_blind_search.which import which
from myDataCatalog import DB


def rerun_analysis(rerun_analysis_path, met_start, duration, counts, outfile, logfile, config):
    # TODO: Convert this call to run on the farm

    print("Running an analysis")

    log_path = os.path.abspath(os.path.expandvars(
        os.path.expanduser(config.get("Real time", "base_path") + "/" + str(met_start) + "_" +
                           str(duration) + "_farm_log.txt")))

    # format the command we will execute
    rerun_analysis_cmd_line = ("qsub -j oe -o %s -F ' --met_start %s --duration %s --counts %s --outfile %s --logfile "
                               "%s --config %s' %s" % (log_path, met_start, duration, counts, outfile, logfile, config,
                                                       rerun_analysis_path))

    # if you want to run locally, use this command line
    # rerun_analysis_cmd_line = ("%s --met_start %s --duration %s --counts %s --outfile %s --logfile %s --config %s" %
    #                            (rerun_analysis_path, met_start, duration, counts, outfile, logfile, config))

    print(rerun_analysis_cmd_line)

    # execute ltf_rerun_analysis.py
    subprocess.check_call(rerun_analysis_cmd_line, shell=True)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='Path to config file', type=get_config, required=True)
    parser.add_argument('--test_time', help='For testing purposes. Sets the most_recent_event_time instead of selecting'
                                            'the time of the most recent recorded event', type=float, required=False)

    args = parser.parse_args()

    configuration = args.config

    # get the interval to rerun analyses over and convert them to seconds
    start_rerun_interval = int(configuration.get("Real time", "start_interval")) * 3600
    end_rerun_interval = int(configuration.get("Real time", "end_interval")) * 3600

    # start a connection with the database storing analysis and transient candidates
    real_time_db = Database(configuration)

    if args.test_time is None:
        # get the time of the most recent event
        event_db = DB.DB()
        c = event_db.query(''' select max(MET_stop) from FT1''')
        most_recent_event_time = c.fetchall()[0][0]
    else:
        # we want to run the script as if this is the most recent event time
        most_recent_event_time = args.test_time

    # TODO: remove this
    # most_recent_event_time = 410227203.000
    print(most_recent_event_time - end_rerun_interval)

    print("most recent event: %s" % most_recent_event_time)

    print("Fetching all analyses that were run using data from %s to %s" %
          (most_recent_event_time - start_rerun_interval, most_recent_event_time - end_rerun_interval - 1))

    # fetch all analyses that were run using data from the interval we wish to rerun
    # subtract an extra 1 from the second time bc get_analysis_between_times is inclusive, and we separately run
    # analysis of the the analysis from most_recent_event_time - end_rerun_interval to most_recent_event_time
    analyses_to_run = real_time_db.get_analysis_between_times(most_recent_event_time - start_rerun_interval,
                                                              most_recent_event_time - end_rerun_interval - 1)

    # get the path to ltf_rerun_analysis.py
    rerun_analysis_path = which("ltf_rerun_analysis.py")

    for row in analyses_to_run:
        print(row)
        # start a job on the farm that runs ltf_rerun_analysis.py
        rerun_analysis(rerun_analysis_path, row.met_start, row.duration, row.counts, row.outfile,
                       row.logfile, configuration.config_file)

    print("finished reruning past analyses, getting the most recent analysis")
    # run an analysis from most_recent_event_time - end_rerun_interval to most_recent_event

    # check if the same analysis has already been run
    most_recent_analysis = real_time_db.get_analysis_between_times(most_recent_event_time - end_rerun_interval,
                                                                   most_recent_event_time)
    if len(most_recent_analysis) == 0:
        # this analysis will be run for the first time

        # add the analysis to the database with 0 as counts (will be replaced when the analysis is actually run)
        print("adding analysis to database")
        analysis_vals = {'met_start': most_recent_event_time - end_rerun_interval, 'duration': end_rerun_interval,
                         'counts': 0, 'outfile': "out.txt", 'logfile': "log.txt"}
        real_time_db.add_analysis(analysis_vals)

        # run the analysis
        rerun_analysis(rerun_analysis_path, most_recent_event_time - end_rerun_interval, end_rerun_interval, 0,
                       "out.txt", "log.txt", configuration.config_file)
    else:
        # TODO: Add check that there is only one results returned??
        # this analysis has been run before so we want to rerun it with the same parameters
        row = most_recent_analysis[0]
        rerun_analysis(rerun_analysis_path, row.met_start, row.duration, row.counts, row.outfile, row.logfile,
                       configuration.config_file)
