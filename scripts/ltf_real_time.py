#!/usr/bin/env python

import argparse
import subprocess

from fermi_blind_search.configuration import get_config
from fermi_blind_search.database import Database
from fermi_blind_search.which import which
from myDataCatalog import DB


def rerun_analysis(rerun_analysis_path, met_start, duration, counts, outfile, logfile, config):
    # TODO: Convert this call to run on the farm

    # format the command we will execute
    rerun_analysis_cmd_line = ("%s --met_start %s --duration %s --counts %s --outfile %s --logfile %s --config %s" %
                               (rerun_analysis_path, met_start, duration, counts, outfile, logfile, config))

    print(rerun_analysis_cmd_line)

    # execute ltf_rerun_analysis.py
    subprocess.check_call(rerun_analysis_cmd_line, shell=True)


if __name__ == "__main__":

    # TODO: figure out how to handle the analysis of the past 12 hours

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='Path to config file', type=get_config, required=True)

    args = parser.parse_args()

    configuration = args.config

    # get the interval to rerun analyses over and convert them to seconds
    start_rerun_interval = int(configuration.get("Real time", "start_interval")) * 3600
    end_rerun_interval = int(configuration.get("Real time", "end_interval")) * 3600

    # start a connection with the database
    real_time_db = Database(configuration)

    # get the time of the most recent event
    event_db = DB.DB()
    c = event_db.query(''' select max(MET_stop) from FT1''')
    most_recent_event_time = c.fetchall()[0][0]

    print("Fetching all analyses that were run using data from %s to %s" %
          (most_recent_event_time - start_rerun_interval, most_recent_event_time - end_rerun_interval))

    # fetch all analyses that were run using data from the interval we wish to rerun
    analyses_to_run = real_time_db.get_analysis_between_times(most_recent_event_time - start_rerun_interval,
                                                              most_recent_event_time - end_rerun_interval)

    # get the path to ltf_rerun_analysis.py
    rerun_analysis_path = which("ltf_rerun_analysis.py")

    for row in analyses_to_run:
        print(row)
        # start a job on the farm that runs ltf_rerun_analysis.py
        rerun_analysis(rerun_analysis_path, row.met_start, row.duration, row.counts, row.outfile,
                                    row.logfile, configuration.config_file)

    # run an analysis from most_recent_event_time - end_rerun_interval to most_recent_event

    # check if the same analysis has already been run
    most_recent_analysis = real_time_db.get_analysis_between_times(most_recent_event_time - end_rerun_interval,
                                                                   most_recent_event_time)
    if len(most_recent_analysis) == 0:
        # this analysis will be run for the first time
        rerun_analysis(rerun_analysis_path, most_recent_event_time - end_rerun_interval, end_rerun_interval, 0,
                       "out.txt", "log.txt", configuration.config_file)

        # add the analysis to the database with 0 as counts (will be replaced when the analysis is actaully run)
        analysis_vals = {'start_met': most_recent_event_time - end_rerun_interval, 'duration': end_rerun_interval,
                         'counts': 0, 'outfile': "out.txt", 'logfile': "log.txt"}
        real_time_db.add_analysis(analysis_vals)
    else:
        # this analysis has been run before so we want to rerun it with the same parameters
        row = most_recent_analysis[0]
        rerun_analysis(rerun_analysis_path, row.met_start, row.duration, row.counts, row.outfile, row.logfile,
                       configuration.config_file)
