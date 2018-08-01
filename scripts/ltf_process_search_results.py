#!/usr/bin/env python
import argparse
import sys

from fermi_blind_search.configuration import get_config
from fermi_blind_search.process_blind_search_results import read_results, already_in_db, get_blocks
from fermi_blind_search import myLogging
from fermi_blind_search.email_blind_search_results import send_email_and_update_db


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="""Format and send an email from a
                                    lft_search results file""")
    parser.add_argument('--results', help='Path to the results file', type=str,
                        required=True)
    parser.add_argument('--config', help='Path to the configuration file',
                        type=get_config, required=True)

    args = parser.parse_args()

    logger = myLogging.log.getLogger("ltf_process_search_results")

    logger.debug("Arguments: %s" % (args.__dict__))

    configuration = args.config
    # read each detected transient into a dictionary and store them as a list
    logger.info("Reading the results stored in %s" % args.results)
    events = read_results(args.results)

    # now events is of the form events[i] = dictionary of information about the transient
    # on line i of the results file

    logger.info("Getting the blocks to email for each event")
    blocks_to_email = []
    for i in range(len(events)):
        # for each detected transient, determine the number of blocks that should be
        # emailed and get their start and stop times
        logger.info("Getting blocks for the event %s" % events[i])
        blocks = get_blocks(events[i])
        logger.info("Found the following blocks: %s" % blocks)
        blocks_to_email.append(blocks)

    # now blocks_to_email[i] = [block_1, block_2, ...]  where block_<#> is a dictionary
    # of the start and stop times of one of the blocks to be emailed for detected transient i

    logger.info("Updating the database for each block")
    for i in range(len(events)):
        ra = events[i]['ra']
        dec = events[i]['dec']

        for j in range(len(blocks_to_email[i])):
            logger.info("Checking if the block with these parameters is in the db: block: %s, ra: %s, dec: %s" %
                        (blocks_to_email[i][j], ra, dec))
            in_db, result = already_in_db(blocks_to_email[i][j], ra, dec, configuration)
            if in_db:
                logger.info("The block was already in the database, not sending email")
            else:
                logger.info("The block was not in the database")

                # we went to send an email about this block
                send_email_and_update_db(result, configuration)

                logger.info("Email sent and block updated to email=True in database")
