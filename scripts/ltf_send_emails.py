#!/usr/bin/env python

import argparse

from fermi_blind_search.configuration import get_config
from fermi_blind_search.email_blind_search_results import query_db_and_send_emails, query_db_and_write


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help="Path to configuration file", type=get_config, required=True)
    parser.add_argument('--email', help='If active send email', action="store_true")
    parser.add_argument('--write_path', help='Path to write results, if they are not emailed', type=str, default='',
                        required=False)

    args = parser.parse_args()
    configuration = args.config

    if args.email:
        # we want to send an email
        query_db_and_send_emails(configuration)
    else:
        # we want to write the "emails" to a file
        query_db_and_write(configuration, args.write_path)
