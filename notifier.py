# Agent to send email to buy or sell a stock
import smtplib, ssl
import configparser
config = configparser.ConfigParser()
config.read('config.ini')

class Notifier:
    def __init__(self, server, port, sender, sender_pwd):
        self.server = server
        self.port = port
        self.sender = sender
        self.sender_pwd = sender_pwd
        self.receiver = ""
    
    def set_receiver(self, receiver_email):
        self.receiver = receiver_email

    def send_email(self, subject: str, content: str):
        context = ssl.create_default_context()
        message = f"""Subject: {subject}

{content}
"""
        try:
            server = smtplib.SMTP(self.server,int(self.port))
            server.ehlo() # Can be omitted
            server.starttls(context=context) # Secure the connection
            server.ehlo() # Can be omitted
            server.login(self.sender, self.sender_pwd)
            server.sendmail(self.sender, self.receiver, message)
        except Exception as e:
            print(f"ERROR - {str(e)}")
            return 1
        finally:
            server.quit()
        return 0