#!/usr/bin/env python

import argparse
import sys

from fermi_blind_search.configuration import get_config
from fermi_blind_search.email_blind_search_results import query_db_and_send_emails, query_db_and_write
from fermi_blind_search import myLogging


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help="Path to configuration file", type=get_config, required=True)
    parser.add_argument('--email', help='If active send email', action="store_true")
    parser.add_argument('--write_path', help='Path to write results, if they are not emailed', type=str, default='',
                        required=False)

    args = parser.parse_args()

    logger = myLogging.log.getLogger("ltf_send_emails")

    # Now overwrite stdout and stderr so they will go to the logger
    sl = myLogging.StreamToLogger(logger, myLogging.log.DEBUG)
    sys.stdout = sl

    sl = myLogging.StreamToLogger(logger, myLogging.log.ERROR)
    sys.stderr = sl

    logger.debug("Arguments: %s" % (args.__dict__))

    configuration = args.config

    if args.email:
        # we want to send an email
        logger.info("We want to send emails")
        query_db_and_send_emails(configuration)
    else:
        # we want to write the "emails" to a file
        logger.email("We want to write the emails to a file instead of sending them")
        query_db_and_write(configuration, args.write_path)
