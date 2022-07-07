import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from jinja2 import Environment, FileSystemLoader
import os

def send_email(host, port, from_addr, to_addr, cc_addr=None, username=None, password=None, **kwargs):
    """
    Utility Method to send email
    :param host: smtp host
    :param port: smtp port
    :param fromaddr: from email addr
    :param toaddr: to email addr
    :return: None
    """
    # creates SMTP session
    email_c = smtplib.SMTP(host, port)
    if username and password:
        email_c.ehlo()
        email_c.starttls()
        email_c.login(username, password)
    to_addr = to_addr.replace(" ", "")
    to_addr_list = to_addr.split(",")
    msg = MIMEMultipart()
    msg['From'] = from_addr
    msg['Cc'] = cc_addr
    msg['Subject'] = "Automation Execution for Transaction ID %s is %s"\
                     % (kwargs.get('task_id'), kwargs.get('status'))
    env = Environment(loader=FileSystemLoader('%s/templates/' % os.path.dirname(__file__)))

    template = env.get_template('email_template.html')
    output = template.render(**kwargs)
    msg.attach(MIMEText(output, 'html'))
    msg['To'] = to_addr
    # email.starttls()
    # authentication
    # email.login(fromaddr, "Password_of_the_sender")
    message = msg.as_string()
    email_c.sendmail(from_addr, to_addr_list, message)
    email_c.quit()
