import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate

gmail_account = "batman.btm.00@gmail.com"
password = "dgsetktoyhixqrdl"

def send_email(subject, body, from_address, to_address):

    # connect SMTP server
    smtpobj = smtplib.SMTP('smtp.gmail.com', 587, timeout=30)
    smtpobj.starttls()
    smtpobj.login(gmail_account, password)

    # generate the email
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_address
    msg['TO'] = to_address
    msg['Date'] = formatdate()

    # send the email
    smtpobj.send_message(msg)
    smtpobj.close()

# send_email("test", "test", gmail_account, gmail_account)