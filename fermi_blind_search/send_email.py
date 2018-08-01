import smtplib

from email.mime.text import MIMEText
from fermi_blind_search import myLogging

_logger = myLogging.log.getLogger("send_email")


def send_email(host, port, username, email_string, recipients, subject):
    # recipients should be a string of the form "person1@email.com,person2@email.com"

    global _logger

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
