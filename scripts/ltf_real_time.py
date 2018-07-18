#!/usr/bin/env python

import argparse
from datetime import datetime

from fermi_blind_search.configuration import get_config
from fermi_blind_search.database import Database
from fermi_blind_search.date2met_converter import convert_date

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
    db = Database(configuration)

    # get the current time and convert it to MET
    # TODO: should this be set to a specific time zone to avoid issues with moving to a new timezone?
    current_time = datetime.now()
    current_time_met = convert_date(str(current_time))

    print("Fetching all analyses that were run using data from %s to %s" % (current_time_met - start_rerun_interval,
          current_time_met - end_rerun_interval))

    # fetch all analyses that were run using data from the interval we wish to rerun
    analyses_to_run = db.get_analysis_between_times(current_time_met - start_rerun_interval, current_time_met - end_rerun_interval)

    for row in analyses_to_run:
        print(row)
        # start a job on the farm that runs ltf_rerun_analysis.py
