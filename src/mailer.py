import os
import random
import smtplib
import time
from email.message import EmailMessage
from email.utils import formataddr

from translations import get_translation

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_TIMEOUT_SECONDS = 60
# Visible sender of the email and address that always receives a copy of every certificate
CERTIFICATES_ADDRESS = "certificats@asbtec.cat"
CERTIFICATES_NAME = "Certificats ASBTEC"


# Builds the certificate email in the language of the course, with the PDF attached.
def build_certificate_email(to_address, partner_name, course_name, language, pdf_path):
    translation = get_translation(language)
    message = EmailMessage()
    message["Subject"] = translation["email_subject"]
    message["From"] = formataddr((CERTIFICATES_NAME, CERTIFICATES_ADDRESS))
    message["To"] = formataddr((partner_name, to_address))
    message.set_content(translation["email_body"].format(partner_name=partner_name, course_name=course_name))
    with open(pdf_path, "rb") as pdf:
        message.add_attachment(pdf.read(), maintype="application", subtype="pdf", filename=os.path.basename(pdf_path))
    return message


# Sends emails through a single SMTP connection, logging in once for the whole run instead of once per email (Gmail
# refuses logins that come too fast with "454 Too many login attempts"). Temporary failures (SMTP 4xx replies, network
# errors, the server closing the connection) reconnect and retry with exponential backoff. Permanent SMTP errors (5xx,
# e.g. wrong password or invalid recipient) are not retried, since more failed logins make a lockout worse.
class Mailer:
    def __init__(self, username, password, envelope_from, retries, retry_base_seconds):
        self.username = username
        self.password = password
        self.envelope_from = envelope_from
        self.retries = retries
        self.retry_base_seconds = retry_base_seconds
        self.smtp = None

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def _connect(self):
        self.smtp = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS)
        self.smtp.login(self.username, self.password)

    def close(self):
        if self.smtp is not None:
            try:
                self.smtp.quit()
            except (smtplib.SMTPException, OSError):
                pass
            self.smtp = None

    # Sends the message to its recipient plus the certificates address. Raises the last error if it could not be sent.
    def send(self, message, to_address):
        recipients = [to_address, CERTIFICATES_ADDRESS]
        for attempt in range(self.retries + 1):
            # After a permanent recipient refusal the connection is still valid: keep it to avoid another login
            reconnect = True
            try:
                if self.smtp is None:
                    self._connect()
                refused = self.smtp.send_message(message, from_addr=self.envelope_from, to_addrs=recipients)
                if to_address in refused:
                    code, reply = refused[to_address]
                    raise smtplib.SMTPRecipientsRefused({to_address: (code, reply)})
                return
            except smtplib.SMTPRecipientsRefused as error:
                transient = all(400 <= code < 500 for code, _ in error.recipients.values())
                reconnect = transient
                last_error = error
            except smtplib.SMTPResponseException as error:
                # Includes login (SMTPAuthenticationError), sender and data errors
                transient = 400 <= error.smtp_code < 500
                last_error = error
            except (smtplib.SMTPServerDisconnected, OSError) as error:
                # Other SMTP errors are OSError subclasses too: they are programming errors, not network ones
                if isinstance(error, smtplib.SMTPException) and not isinstance(error, smtplib.SMTPServerDisconnected):
                    raise
                transient = True
                last_error = error

            if reconnect:
                self.close()
            if not transient or attempt == self.retries:
                raise last_error
            wait = self.retry_base_seconds * 2 ** attempt + random.uniform(0, self.retry_base_seconds)
            print(f"Temporary email error ({last_error}), retry {attempt + 1} of {self.retries} in {wait:.0f} s")
            time.sleep(wait)
