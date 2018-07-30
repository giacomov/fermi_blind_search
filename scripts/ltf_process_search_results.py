#!/usr/bin/env python
import argparse

from fermi_blind_search.configuration import get_config
from fermi_blind_search.process_blind_search_results import read_results, already_in_db, get_blocks


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="""Format and send an email from a
                                    lft_search results file""")
    parser.add_argument('--results', help='Path to the results file', type=str,
                        required=True)
    parser.add_argument('--config', help='Path to the configuration file',
                        type=get_config, required=True)

    args = parser.parse_args()

    configuration = args.config
    # read each detected transient into a dictionary and store them as a list
    events = read_results(args.results)

    # now events is of the form events[i] = dictionary of information about the transient
    # on line i of the results file

    blocks_to_email = []
    for i in range(len(events)):
        # for each detected transient, determine the number of blocks that should be
        # emailed and get their start and stop times
        blocks_to_email.append(get_blocks(events[i]))

    # now blocks_to_email[i] = [block_1, block_2, ...]  where block_<#> is a dictionary
    # of the start and stop times of one of the blocks to be emailed for detected transient i

    for i in range(len(events)):
        ra = events[i]['ra']
        dec = events[i]['dec']

        for j in range(len(blocks_to_email[i])):
            already_in_db(blocks_to_email[i][j], ra, dec, configuration)
