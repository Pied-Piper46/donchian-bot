import smtplib

print("shit")
smtpobj = smtplib.SMTP('smtp.gmail.com', 465)
print("shit")
smtpobj.ehlo()
smtpobj.starttls()
smtpobj.ehlo()
smtpobj.login("batman.btm.00@gmail.com", "dgsetktoyhixqrdl")