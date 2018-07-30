import smtplib

from fermi_blind_search.database import Database
from email.mime.text import MIMEText


def format_email(block):

    # using the start time, interval, ra, and dec of the blocks we need to email, format
    # the body of the email

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