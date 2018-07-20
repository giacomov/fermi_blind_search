#!/usr/bin/env python
import argparse
import smtplib
import numpy as np

from fermi_blind_search.configuration import get_config
from fermi_blind_search.database import Database


def read_results(filename):

    print("reading results from file")
    data = np.recfromtxt(filename, delimiter=' ', names=True, encoding=None)

    events = []

    if data.size == 1:
        print("size 1")
        # when there is only one result, we have to deal with the recarray differently
        # because the types of the values is different
        events.append({'name': str(data.name.reshape(1,)[0]), 'ra': float(data.ra.reshape(1,)[0]),
                       'dec': float(data.dec.reshape(1,)[0]),
                       'start_times': [float(j) for j in str(data.tstarts.reshape(1,)[0]).split(',')],
                       'stop_times': [float(j) for j in str(data.tstops.reshape(1,)[0]).split(',')],
                       'counts': [float(j) for j in str(data.counts.reshape(1,)[0]).split(',')],
                       'probs': [float(j) for j in str(data.probabilities.reshape(1,)[0]).split(',')]})
    else:
        print("other size")
        for i in range(len(data)):
            # we convert start_times stop_time, counts, and probs to float values because they will be used
            # for comparisons when determining which blocks to include in the email
            events.append({'name': str(data[i].name), 'ra': float(data[i].ra), 'dec': float(data[i].dec),
                           'start_times': [float(j) for j in str(data[i].tstarts).split(',')],
                           'stop_times': [float(j) for j in str(data[i].tstops).split(',')],
                           'counts': [float(j) for j in str(data[i].counts).split(',')],
                           'probs': [float(j) for j in str(data[i].probabilities).split(',')]})

    return events


def get_blocks(event_dict):

    # we want to find the X blocks with lowest probability, so we do an
    # argmin-like operation to get their indices in event_dict
    sorted_list_idx = sorted(range(len(event_dict['probs'])), key=(lambda index: event_dict['probs'][index]))

    # number of blocks the Bayseian Blocks algorithm detected
    num_blocks = len(event_dict['start_times'])

    # store the return values here
    blocks_to_email = []

    assert num_blocks > 1, "There is zero or one blocks in the input file. This should never happen."

    if num_blocks <= 3:

        # there are 2 or 3 blocks and we want to email the one with lowest probability
        lowest_prob_idx = sorted_list_idx[0]
        blocks_to_email.append({'start_time': event_dict['start_times'][lowest_prob_idx],
                                'stop_time': event_dict['stop_times'][lowest_prob_idx]})

    elif num_blocks == 4:

        # there are 4 blocks, we want to return the two with lowest probaility, returning them as
        # one block if they are continuous
        lowest_prob_idx = sorted_list_idx[0]
        second_prob_idx = sorted_list_idx[1]

        if abs(lowest_prob_idx - second_prob_idx) == 1:

            # the blocks are continuous, return as one block that contains the two smaller blocks
            start_time = min(event_dict['start_times'][lowest_prob_idx], event_dict['start_times'][second_prob_idx])
            stop_time = max(event_dict['stop_times'][lowest_prob_idx], event_dict['stop_times'][lowest_prob_idx])
            blocks_to_email.append({'start_time': start_time, 'stop_time': stop_time})

        else:

            # the blocks are non-continuous, so we want to return them as two separate blocks
            blocks_to_email.append({'start_time': event_dict['start_times'][lowest_prob_idx],
                                    'stop_time': event_dict['stop_times'][lowest_prob_idx]})
            blocks_to_email.append({'start_time': event_dict['start_times'][second_prob_idx],
                                    'stop_time': event_dict['stop_times'][second_prob_idx]})
    else:

        # there are more than 4 blocks, we want to return the three with lowest probability, returning
        # continuous blocks as one block

        # returns the blocks with minimum probability in the order in which they occurr in time
        sorted_min_three = sorted([sorted_list_idx[0], sorted_list_idx[1], sorted_list_idx[2]])

        # start by appending the first block (in time) to the list. The end time of this block
        # may be updated if it is continuous with the next block
        blocks_to_email.append({'start_time': event_dict['start_times'][sorted_min_three[0]],
                                'stop_time': event_dict['stop_times'][sorted_min_three[0]]})

        for i in range(1, 3):
            if sorted_min_three[i] - sorted_min_three[i-1] == 1:

                # the blocks are continuous, update the block in blocks_to_email to have a later stop_time
                blocks_to_email[-1]['stop_time'] = event_dict['stop_times'][sorted_min_three[i]]

            else:

                # the blocks are not continuous, so add a new block to blocks_to_email
                blocks_to_email.append({'start_time': event_dict['start_times'][sorted_min_three[i]],
                                        'stop_time': event_dict['stop_times'][sorted_min_three[i]]})
    return blocks_to_email


def format_email(block_dict, ra, dec):

    # using the start and stop times, ra, and dec of the blocks we need to email, format
    # the body of the email

    interval = block_dict['stop_time'] - block_dict['start_time']

    string = ('TITLE: GCN/GBM NOTICE \nNOTICE_TYPE: User-supplied job \nGRB_RA: %s \nGRB_DEC: %s \nGRB_MET: %s \nANALYSIS_INTERVAL: %s\n'
              % (str(ra), str(dec), str(block_dict['start_time']), str(interval)))

    return string


def write_to_file(email_string, name):

    with open(name, 'w+') as f:
        f.write(email_string)


def already_in_db(block_dict, ra, dec, config):
    #returns true if the block is in the db

    # get the interval of the transient
    interval = block_dict['stop_time'] - block_dict['start_time']

    # set up the dictionary to check against the db
    new_block_dict = {'ra': float(ra), 'dec': float(dec), 'met_start': block_dict['start_time'], 'interval': interval}

    print(new_block_dict)
    # establish db connection
    db = Database(config)

    # get any transients that match ours
    matches = db.get_results(new_block_dict)

    print(matches)
    print(len(matches) > 0)

    if len(matches) == 0:
        # add the candidate to the database
        db.add_candidate(new_block_dict)

    return len(matches) > 0


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="""Format and send an email from a
                                    lft_search results file""")
    parser.add_argument('--results', help='Path to the results file', type=str,
                        required=True)
    parser.add_argument('--email', help='If active send email', action="store_true")
    parser.add_argument('--config', help='Path to the configuration file',
                        type=get_config, required=True)
    parser.add_argument('--check_db', help='If active check each block against the database of found transients',
                        action="store_true")

    args = parser.parse_args()

    configuration = args.config
    print(args.check_db)
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

    if args.email:

        # # open the smtp email server and login
        # s = smtplib.SMTP(host=configuration.get("Results email", "host"),
        #                   port=int(configuration.get("Results email", "port")))
        # s.starttls()
        # s.login(configuration.get("Results email", "username"), configuration.get("Results email", "pword"))

        server = smtplib.SMTP(configuration.get("Results email", "host"),
                              port=int(configuration.get("Results email", "port")))

        try:
            for i in range(len(events)):

                # the ra and dec do not change for each block
                ra = events[i]['ra']
                dec = events[i]['dec']

                for j in range(len(blocks_to_email[i])):
                    if args.check_db and already_in_db(blocks_to_email[i][j], ra, dec, configuration):
                        # the transient is already in the database, don't send another email
                        print("transient candidate already found, not sending email")
                    else:
                        print('back in email part')
                        print(blocks_to_email[i][j])
                        # format the body of the email
                        email_body = format_email(blocks_to_email[i][j], ra, dec)

                        server.sendmail(configuration.get("Results email", "username"),
                                        configuration.get("Results email", "recipient"),
                                        email_body)

                    # send the email
                    # msg = MIMEText(email_body)
                    # msg['From'] = configuration.get("Results email", "username")
                    # msg['To'] = configuration.get("Results email", "recipient")
                    # msg['Subject'] = configuration.get("Results email", "subject")
                    # s.sendmail(configuration.get("Results email", "username"),
                    #           [configuration.get("Results email", "recipient")], msg.as_string())
                    # del msg
        except:

            raise

        finally:

            # terminate the email server session
            server.quit()

    else:

        # we want to write the emails to a .txt file instead of sending them

        for i in range(len(events)):

            # for each detected transient we want to write a file for each block

            # the ra and dec do not change for each block
            ra = events[i]['ra']
            dec = events[i]['dec']

            for j in range(len(blocks_to_email[i])):
                if args.check_db and already_in_db(blocks_to_email[i][j], ra, dec, configuration):
                    # the transient is already in the database, don't send another email
                    print("transient candidate already found, not writing to file")
                else:
                    print('back in email part')
                    print(blocks_to_email[i][j])
                    # format the body of the "email"
                    email_body = format_email(blocks_to_email[i][j], ra, dec)

                    # write the file using the filename format <name_of_transient>_block<#>
                    write_to_file(email_body, events[i]['name'] + '_block' + str(j))
