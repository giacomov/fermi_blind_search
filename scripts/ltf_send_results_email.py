#!/usr/bin/env python
import argparse
import smtplib
from email.mime.text import MIMEText
import os

def valid_configuration(s):

    # Set environment
    os.environ['LTF_CONFIG_FILE'] = s

    # Get configuration
    from fermi_blind_search.Configuration import configuration

    return configuration

def read_results(filename):

    f = open(filename)

    #each detected transient is written on a new line
    results_list = f.read().split('\n')

    f.close()

    #store the return values here
    events = []

    #the first line of the file is the header, so we ignore this by starting at index 1
    for i in range(1,len(results_list)):

        #splits on all whitespace
        e = results_list[i].split()

        #there may be a newline at the end of the file, we want to ignore it
        if len(e) > 0:

            #we convert start_times stop_time, counts, and probs to float values because they will be used
            #for comparisons when determining which blocks to include in the email
            events.append({'name': e[0], 'ra': e[1], 'dec': e[2],
                            'start_times': [float(i) for i in e[3].split(',')],
                            'stop_times': [float(i) for i in e[4].split(',')],
                            'counts': [float(i) for i in e[5].split(',')],
                            'probs': [float(i) for i in e[6].split(',')]})
    return events

def get_blocks(event_dict):

    #we want to find the X blocks with lowest probaility, so we do an
    #argmin-like operation to get their indices in event_dict
    sorted_list_idx = sorted(range(len(event_dict['probs'])),
                            key=(lambda index: event_dict['probs'][index]))

    #number of blocks the Bayseian Blocks algorithm detected
    num_blocks = len(event_dict['start_times'])

    #store the return values here
    blocks_to_email = []

    if num_blocks <= 3:

        #there are 2 or 3 blocks and we want to email the one with lowest probability
        lowest_prob_idx = sorted_list_idx[0]
        blocks_to_email.append({'start_time': event_dict['start_times'][lowest_prob_idx],
                                'stop_time': event_dict['stop_times'][lowest_prob_idx]})

    if num_blocks == 4:

        #there are 4 blocks, we want to return the two with lowest probaility, returning them as
        #one block if they are continuous
        lowest_prob_idx = sorted_list_idx[0]
        second_prob_idx = sorted_list[1]

        if abs(lowest_prob_idx - second_prob_idx) == 1:

            #the blocks are continuous, return as one block that contains the two smaller blocks
            start_time = min(event_dict['start_times'][lowest_prob_idx],
                            event_dict['start_times'][second_prob_idx])
            stop_time = max(event_dict['stop_times'][lowest_prob_idx],
                            event_dict['stop_times'][lowest_prob_idx])
            blocks_to_email.append({'start_time': start_time, 'stop_time': stop_time})

        else:

            #the blocks are non-continuous, so we want to return them as two separate blocks
            blocks_to_email.append({'start_time': event_dict['start_times'][lowest_prob_idx],
                                    'stop_time': event_dict['stop_times'][lowest_prob_idx]})
            blocks_to_email.append({'start_time': event_dict['start_times'][second_prob_idx],
                                    'stop_time': event_dict['stop_times'][second_prob_idx]})
    else:

        #there are more than 4 blocks, we want to return the three with lowest probability, returning
        #continuous blocks as one block

        #returns the blocks with minimum probability in the order in which they occurr in time
        sorted_min_three = sorted([sorted_list_idx[0], sorted_list_idx[1], sorted_list_idx[2]])

        #start by appending the first block (in time) to the list. The end time of this block
        #may be updated if it is continuous with the next block
        blocks_to_email.append({'start_time': event_dict['start_times'][sorted_min_three[0]],
                                'stop_time': event_dict['stop_times'][sorted_min_three[0]]})

        for i in range(1,3):
            if sorted_min_three[i] - sorted_min_three[i-1] == 1:

                #the blocks are continuous, update the block in blocks_to_email to have a later stop_time
                blocks_to_email[-1]['stop_time'] = event_dict['stop_times'][sorted_min_three[i]]

            else:

                #the blocks are not continuous, so add a new block to blocks_to_email
                blocks_to_email.append({'start_time': event_dict['start_times'][sorted_min_three[i]],
                                        'stop_time': event_dict['stop_times'][sorted_min_three[i]]})
    return blocks_to_email


def format_email(block_dict, ra, dec):

    # using the start and stop times, ra, and dec of the blocks we need to email, format
    # the body of the email

    interval = block_dict['stop_time'] - block_dict['start_time']

    string = ('TITLE: GCN/GBM NOTICE \nNOTICE_TYPE: User-supplied job \nGRB_RA: %s \nGRB_DEC: %s \nGRB_MET: %s \nANALYSIS_INTERVAL: %s\n'
            % (ra, dec, str(block_dict['start_time']), str(interval)))

    return string


def write_to_file(email_string, name):

    f = open(name, 'w+')
    f.write(email_string)
    f.close()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="""Format and send an email from a
                                    lft_search results file""")
    parser.add_argument('--results', help='Path to the results file', type=str,
                        required=True)
    parser.add_argument('--email', help='If active send email', action="store_true")
    parser.add_argument('--config', help='Path to the configuration file',
                        type=valid_configuration, required=True)

    args = parser.parse_args()

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

        from fermi_blind_search.Configuration import configuration

        # open the smtp email server and login
        s = smtplib.SMTP(host=configuration.get("Results email", "host"), port=int(configuration.get("Results email", "port")))
        s.starttls()
        s.login(configuration.get("Results email", "username"), configuration.get("Results email", "pword"))

        for i in range(len(events)):

            # for each detected transient, we want to send an email for each block

            # the ra and dec do not change for each block
            ra = events[i]['ra']
            dec = events[i]['dec']

            for j in range(len(blocks_to_email[i])):

                # format the body of the email
                email_body = format_email(blocks_to_email[i][j], ra, dec)

                # send the email
                msg = MIMEText(email_body)
                msg['From'] = configuration.get("Results email", "username")
                msg['To'] = configuration.get("Results email", "recipient")
                msg['Subject'] = configuration.get("Results email", "subject")
                s.sendmail(configuration.get("Results email", "username"), [configuration.get("Results email", "recipient")], msg.as_string())
                del msg

        # terminate the email server session
        s.quit()

    else:

        # we want to write the emails to a .txt file instead of sending them

        for i in range(len(events)):

            # for each detected transient we want to write a file for each block

            # the ra and dec do not change for each block
            ra = events[i]['ra']
            dec = events[i]['dec']

            for j in range(len(blocks_to_email[i])):

                # format the body of the "email"
                email_body = format_email(blocks_to_email[i][j], ra, dec)

                # write the file using the filename format <name_of_transient>_block<#>
                write_to_file(email_body, events[i]['name'] + '_block' + str(j))
