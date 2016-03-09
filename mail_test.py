#!/usr/bin/python
# Adapted from http://kutuma.blogspot.com/2007/08/sending-emails-via-gmail-with-python.html

import smtplib

gmail_user = "testing.oz.255@gmail.com"
gmail_pwd = "Aasdf12345"

class Gmail(object):
    def __init__( self , email , password ):
        self.email = email
        self.password = password
        self.server = 'smtp.gmail.com'
        self.port = 587
        session = smtplib.SMTP( self.server, self.port )
        session.ehlo()
        session.starttls()
        session.ehlo
        session.login(self.email, self.password)
        self.session = session
if cpu.user> 
    def send_message(self, subject, body):
        headers = [
            "From: " + self.email,
            "Subject: Mensaje de alerta >> TSO",
            "To: " + subject,
            "MIME-Version: 1.0",
            "Content-Type: text/html"]
        headers = "\r\n".join( headers )
        self.session.sendmail( self.email , subject,  headers + "\r\n\r\n" + body )


gm = Gmail( 'testing.oz.255@gmail.com', 'Aasdf12345' )

#gm.send_message( 'ozzirisc@gmail.com', 'Hola juanquis' )
gm.send_message( 'veizagacabrerajuancarlos.jcvc@gmail.com', 'Hola juanquis, como estas hoy!!!!!' )


