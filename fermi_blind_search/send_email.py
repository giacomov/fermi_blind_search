import smtplib
import getpass
from email.mime.text import MIMEText
from fermi_blind_search import myLogging
import sshtunnel
from configuration import get_config

_logger = myLogging.log.getLogger("send_email")


def send_email(*args, **kwargs):
    """

    :param host: SMTP host
    :param port: SMTP port
    :param username: username to authenticate with
    :param email_string: body of the email (a text string)
    :param recipients: comma-separated list of recipients
    :param subject: subject of the email
    :param tunnel: optional. A tuple (hostname, port, username, key_directory) specifying the SMTP server and its port.
    If this is specified, a SSH tunnel will be open from the local host to this host and the email sent through the
    tunnel.
    NOTE: authentication is not supported, so the SMTP host should accept an SSH connection from the user username with
    public key, to be found in the key_directory
    :return: None
    """

    if 'tunnel' in kwargs:

        # Open tunnel
        tunnel_host, tunnel_port, tunnel_username, key_directory = kwargs['tunnel']

        kwargs.pop('tunnel')

        with sshtunnel.SSHTunnelForwarder(tunnel_host,
                                          ssh_username=tunnel_username,
                                          host_pkey_directories=[key_directory],
                                          remote_bind_address=('127.0.0.1',
                                                               tunnel_port)) as tunnel:


            # Overwrite port to use the tunneled one
            args = list(args)
            args[1] = tunnel.local_bind_port

            _send_email(*args, **kwargs)

    else:

        # No need for tunneling

        _send_email(*args, **kwargs)


def _send_email(host, port, username, email_string, recipients, subject):

    # recipients should be a string of the form "person1@email.com,person2@email.com"

    # open the smtp email server
    server = smtplib.SMTP(host, port=int(port))

    send_to = recipients.split(",")

    # create a MIME object so that the email send correctly
    msg = MIMEText(email_string)
    msg['From'] = username
    msg['To'] = ", ".join(send_to)
    msg['Subject'] = subject

    _logger.info("Sending email from %s to %s with subject %s" % (msg['From'], msg['To'], msg['Subject']))
    _logger.info("Email Body Begins with: %.256s" % email_string)

    # send the email
    try:
        server.sendmail(username, send_to, msg.as_string())
    except:
        raise
    finally:
        del msg
