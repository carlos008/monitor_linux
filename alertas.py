
import smtplib
import ssl
def enviar_alerta( email , mensaje ):
    import smtplib
    correo_gmail = "testing.oz.255@gmail.com"
    contrasenia_gmail = "Aasdf12345"
    servidor = 'smtp.gmail.com'
    puerto = 587

    session = smtplib.SMTP( servidor , puerto )

    session.ehlo()
    session.starttls()
    session.ehlo

    session.login( correo_gmail , contrasenia_gmail )

    headers = [
        "From: " + correo_gmail,
        "Subject: Mensaje de alerta >> TSO",
        "To: " + email,
        "MIME-Version: 1.0",
        "Content-Type: text/html"]
    headers = "\r\n".join( headers )
    
    session.sendmail( correo_gmail , email ,  headers + "\r\n\r\n" + mensaje )

#enviar_alerta( "veizagacabrerajuancarlos.jcvc@gmail.com" , "prueba 0mensaje hola" )