
from fermi_blind_search.database import Database, database_connection
from fermi_blind_search import myLogging
from fermi_blind_search.send_email import send_email

_logger = myLogging.log.getLogger("process_blind_search_results")


def format_email(block):

    # using the start time, interval, ra, and dec of the blocks we need to email, format
    # the body of the email

    _logger.info("Formatting the email body for the block: %s" % block)

    # Todo: get name of algorithm
    # we subtract 0.001 from the start time so that the NAME OF ALGORITHM analyzes data that inlcudes our entire range
    start_time = block.met_start - 0.001

    # we want to round the duration up to 1 significant figure, ex. 729374.038484 -> 800000
    # From some quick research, there isn't a built in or library function that does this operation so we do it manually

    # converting to an int removes the decimal part, then converting to a string allows us to know how many digits
    # the number has.
    duration = str(int(block.interval))

    # we want to get the first digit and add 1 (to round up) and then expand the number back out to have the correct
    # magnitude
    duration = (int(duration[0]) + 1) * 10*(len(duration) - 1)

    string = ('TITLE: GCN/GBM NOTICE \nNOTICE_TYPE: User-supplied job \nGRB_RA: %s \nGRB_DEC: %s \nGRB_MET: %s \nANALYSIS_INTERVAL: %s\n'
              % (str(block.ra), str(block.dec), str(start_time), str(duration)))

    return string


def write_to_file(email_string, name):

    _logger.info("Writing email to the file: %s" % name)

    with open(name, 'w+') as f:
        f.write(email_string)


def query_db_and_send_emails(config):

    _logger.info("Fetching the results that have not been emailed, and sending emails")

    # establish a connection with the database
    db = Database(config)

    # fetch the blocks that haven't been emailed yet
    blocks_to_email = db.get_results_to_email()
    _logger.debug("Successfully fetched results from database")

    _logger.info("There are %s blocks to email" % len(blocks_to_email))

    if len(blocks_to_email) == 0:
        _logger.info("No emails to send, terminating...")

    # if we need to open an ssh tunnel to send the email (see send_email() in send_email.py) set up the ssh_tunnel
    # here and send tunnel=ssh_tunnel to send_email

    for block in blocks_to_email:

        # format the body of the email
        email_body = format_email(block)
        subject = "LTF_REAL_TIME RESULT"

        # send the email
        try:
            send_email(config.get("Email", "host"), config.get("Email", "port"),
                       config.get("Email", "username"), email_body, config.get("Email", "recipient"),
                       subject)
        except:
            raise
        else:
            # if the email has sent, update the database
            db.update_result_email(block, email_val=True)
            _logger.debug("Successfully updated the database")


def send_email_and_update_db(block, config):
    """
    Does not query the database to find the blocks to email, and instead sends an email for the passed block
    :param block: the block (retrieved from database) to email
    :param config: the configuration object storing information for sending the email
    :return: none
    """

    db = Database(config)
    # format the body of the email
    email_body = format_email(block)
    subject = "LTF_REAL_TIME RESULT"

    # if we need to open an ssh tunnel to send the email (see send_email() in send_email.py) set up the ssh_tunnel
    # here and send tunnel=ssh_tunnel to send_email

    # send the email
    try:
        send_email(config.get("Email", "host"), config.get("Email", "port"),
                   config.get("Email", "username"), email_body, config.get("Email", "recipient"),
                   subject)

    except:
        raise
    else:
        # if the email has sent, update the database
        db.update_result_email(block, email_val=True)
        _logger.debug("Successfully updated the database")


def query_db_and_write(config, write_path):

    _logger.info("Fetching the results that have not been emailed and writing the emails we would send to a file")

    # establish connection with database
    db = Database(config)

    # get the blocks that need to be emailed
    blocks_to_email = db.get_results_to_email()

    _logger.info("There are %s blocks to email" % len(blocks_to_email))

    if len(blocks_to_email) == 0:
        _logger.info("No emails to send, terminating...")

    for block in blocks_to_email:
        # format the body of the "email"
        email_body = format_email(block)

        # write the "email" to a file
        write_to_file(email_body, write_path + str(block.start_time) + "_" + str(block.stop_time))