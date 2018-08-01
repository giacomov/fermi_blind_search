import smtplib
import sys

from fermi_blind_search.database import Database, database_connection
from email.mime.text import MIMEText
from fermi_blind_search import myLogging

_logger = myLogging.log.getLogger("process_blind_search_results")


def format_email(block):

    global _logger

    # using the start time, interval, ra, and dec of the blocks we need to email, format
    # the body of the email

    _logger.info("Formatting the email body for the block: %s" % block)

    string = ('TITLE: GCN/GBM NOTICE \nNOTICE_TYPE: User-supplied job \nGRB_RA: %s \nGRB_DEC: %s \nGRB_MET: %s \nANALYSIS_INTERVAL: %s\n'
              % (str(block.ra), str(block.dec), str(block.met_start), str(block.interval)))

    return string


def write_to_file(email_string, name):

    _logger.info("Writing email to the file: %s" % name)

    with open(name, 'w+') as f:
        f.write(email_string)


def query_db_and_send_emails(config):

    global _logger

    _logger.info("Fetching the results that have not been emailed, and sending emails")

    # establish a connection with the database
    with database_connection(config):
        db = Database(config)

        # fetch the blocks that haven't been emailed yet
        blocks_to_email = db.get_results_to_email()
        _logger.debug("Successfully fetched results from database")

        for block in blocks_to_email:
            # open the smtp email server
            server = smtplib.SMTP(config.get("Results email", "host"),
                                  port=int(config.get("Results email", "port")))
            # format the body of the email
            email_body = format_email(block)

            recipients = config.get("Results email", "recipient").split(",")

            # create a MIME object so that the email send correctly
            msg = MIMEText(email_body)
            msg['From'] = config.get("Results email", "username")
            msg['To'] = ", ".join(recipients)
            msg['Subject'] = config.get("Results email", "subject")

            # send the email
            try:
                server.sendmail(config.get("Results email", "username"), recipients, msg.as_string())
            except:
                raise
            else:
                # if the email has sent, update the database
                db.update_result_email(block, email_val=True)
                _logger.debug("Successfully updated the database")
            finally:
                del msg


def query_db_and_write(config, write_path):

    global _logger

    _logger.info("Fetching the results that have not been emailed and writing the emails we would send to a file")

    # establish connection with database
    with database_connection(config):
        db = Database(config)

        # get the blocks that need to be emailed
        blocks_to_email = db.get_results_to_email()

        for block in blocks_to_email:
            # format the body of the "email"
            email_body = format_email(block)

            # write the "email" to a file
            write_to_file(email_body, write_path + str(block.start_time) + "_" + str(block.stop_time))