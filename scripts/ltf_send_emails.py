#!/usr/bin/env python

import argparse
import smtplib

from fermi_blind_search.database import Database
from fermi_blind_search.configuration import get_config
from email.mime.text import MIMEText


def format_email(block):

    # using the start and stop times, ra, and dec of the blocks we need to email, format
    # the body of the email

    # interval = block.stop_time - block.start_time

    string = ('TITLE: GCN/GBM NOTICE \nNOTICE_TYPE: User-supplied job \nGRB_RA: %s \nGRB_DEC: %s \nGRB_MET: %s \nANALYSIS_INTERVAL: %s\n'
              % (str(block.ra), str(block.dec), str(block.met_start), str(block.interval)))

    return string


def write_to_file(email_string, name):

    with open(name, 'w+') as f:
        f.write(email_string)


def query_db_and_send_emails(config):

    # establish a connection with the database
    db = Database(config)

    # fetch the blocks that haven't been emailed yet
    blocks_to_email = db.get_results_to_email()

    for block in blocks_to_email:
        # open the smtp email server
        server = smtplib.SMTP(config.get("Results email", "host"),
                              port=int(config.get("Results email", "port")))
        # format the body of the email
        email_body = format_email(block)

        # create a MIME object so that the email send correctly
        msg = MIMEText(email_body)
        msg['From'] = config.get("Results email", "username")
        msg['To'] = config.get("Results email", "recipient")
        msg['Subject'] = config.get("Results email", "subject")

        # send the email
        try:
            server.sendmail(config.get("Results email", "username"),
                            config.get("Results email", "recipient"),
                            msg.as_string())
        except:
            raise
        else:
            # if the email has sent, update the database
            db.update_result_email(block, email_val=True)
        finally:
            del msg


def query_db_and_write(config, write_path):

    # establish connection with database
    db = Database(config)

    # get the blocks that need to be emailed
    blocks_to_email = db.get_results_to_email()

    for block in blocks_to_email:
        # format the body of the "email"
        email_body = format_email(block)

        # write the "email" to a file
        write_to_file(email_body, write_path + str(block.start_time) + "_" + str(block.stop_time))


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
