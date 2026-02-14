import smtplib
from email.mime.text import MIMEText
import os

def stuur_email(onderwerp, tekst):
    sender = os.environ.get("EMAIL_SENDER") 
    wachtwoord = os.environ.get("EMAIL_PASSWORD") # Gebruik een 'App Wachtwoord'
    ontvanger = os.environ.get("EMAIL_RECEIVER") 

    if not sender or not wachtwoord:
        return "Geen mailgegevens ingesteld."

    msg = MIMEText(tekst, 'html')
    msg['Subject'] = onderwerp
    msg['From'] = sender
    msg['To'] = ontvanger

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, wachtwoord)
            server.sendmail(sender, ontvanger, msg.as_string())
        return "SUCCES: Mail verzonden!"
    except Exception as e:
        return f"FOUT: {e}"