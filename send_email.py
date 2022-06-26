import smtplib
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.utils import formatdate

def send_email(subject, body, from_address, to_address):

    gmail_account = "batman.btm.00@gmail.com"
    password = "dgsetktoyhixqrdl"

    msg = EmailMessage()
    msg.set_content("This is a test.")

    msg['Subject'] = "The subject"
    msg['From'] = gmail_account
    msg['To'] = gmail_account

    print("debug1")
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    s.login(gmail_account, password)

    s.send_message(msg)
    s.quit()



    # # connect SMTP server
    # print("debug")
    # smtpobj = smtplib.SMTP('smtp.gmail.com', 587, timeout=30)
    # smtpobj.starttls()
    # smtpobj.login(gmail_account, password)

    # # generate the email
    # msg = MIMEText(body)
    # msg['Subject'] = subject
    # msg['From'] = from_address
    # msg['TO'] = to_address
    # msg['Date'] = formatdate()

    # # send the email
    # smtpobj.send_message(msg)
    # smtpobj.close()


# send_email("test", "test", "test", "test")



with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
    smtp.set_debuglevel(1)
    smtp.docmd("NOOP")