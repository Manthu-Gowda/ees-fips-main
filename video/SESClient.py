import os
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from decouple import config as ENV_CONFIG
# import ees_logger
from ees_logger import ees_logger

class SESClient:
    def __init__(self):
        # FIPS-compliant SES client
        fips_config = Config(region_name="us-east-2", use_fips_endpoint=True)
        self.ses_client = boto3.client("ses", config=fips_config)
        ees_logger.info(f"SES endpoint URL: {self.ses_client.meta.endpoint_url}")
    def send_email_with_attachment(
        self,
        subject: str,
        body: str,
        to_addresses: list[str],
        cc_addresses: list[str] = None,
        attachment_path=None,
        sender_email: str = ENV_CONFIG("SMTP_EMAIL_FROM_PROD") if ENV_CONFIG("ENVIRONMENT") == "PROD" else ENV_CONFIG("SMTP_EMAIL_FROM_DEV"),
        reply_to_email: str = ENV_CONFIG("REPLY_TO_EMAIL")
    ):
        """
        Send an email with one or multiple attachments (FIPS-compliant).
        - attachment_path can be a string or list of strings.
        """
        ees_logger.info(f"Preparing to send email to: {", ".join(to_addresses)} with subject: {subject}")
        cc_addresses = cc_addresses or []
        print(sender_email,"sender_email")
        # Normalize attachment(s)
        if isinstance(attachment_path, str):
            attachment_paths = [attachment_path]
        elif isinstance(attachment_path, list):
            attachment_paths = attachment_path
        else:
            attachment_paths = []

        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = ", ".join(to_addresses)
        if cc_addresses:
            msg["Cc"] = ", ".join(cc_addresses)
        msg["Reply-To"] = reply_to_email

        # Body
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # Attach files
        for path in attachment_paths:
            if path and os.path.exists(path):
                with open(path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={os.path.basename(path)}",
                    )
                    msg.attach(part)
            else:
                ees_logger.error(f"Attachment not found: {path}")

        # Send email
        try:
            response = self.ses_client.send_raw_email(
                Source=sender_email,
                Destinations=list(set(to_addresses + cc_addresses)),
                RawMessage={"Data": msg.as_string()},
            )
            if response and "MessageId" in response:
                ees_logger.info(f"Email sent! Message ID: {response['MessageId']}")
            return response
        except ClientError as e:
            ees_logger.error(f"Failed to send email: {e.response['Error']['Message']}")
            raise e
        except Exception as e:
            ees_logger.error(f"An unexpected error occurred: {str(e)}")
            raise e