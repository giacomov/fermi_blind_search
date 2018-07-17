#!/usr/bin/env python

import argparse
from datetime import datetime

from fermi_blind_search.configuration import get_config
from fermi_blind_search.database import Database
from fermi_blind_search.date2met_converter import convert_date

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='Path to config file', type=get_config, required=True)

    args = parser.parse_args()

    # start a connection with the database
    db = Database(args.config)

    # get the current time and convert it to MET
    current_time = datetime.now()
    current_time_met = convert_date(str(current_time))

    print("Fetching all analyses that were run using data from %s to %s", current_time_met - 86400, current_time_met - 43200)

    # fetch all analyses that were run using data from 12-24 hours ago
    analyses_to_run = db.get_analysis_between_times(current_time_met - 86400, current_time_met - 43200)

    for row in analyses_to_run:
        print(row)
        # start a job on the farm that runs ltf_rerun_analysis.py
