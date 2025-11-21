import logging
from typing import Optional, List
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
import asyncio

from app.config import settings

logger = logging.getLogger(__name__)

# Optional import for SMTP (only needed if not using AWS SES)
try:
    import aiosmtplib
    HAS_AIOSMTPLIB = True
except ImportError:
    HAS_AIOSMTPLIB = False


class EmailService:
    """Service for sending emails, including Send to Kindle functionality"""

    def __init__(self):
        self.use_aws_ses = settings.use_aws_ses
        self.ses_from_email = settings.ses_from_email
        self.ses_from_name = settings.ses_from_name
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        self.smtp_use_tls = settings.smtp_use_tls
        self.smtp_from_email = settings.smtp_from_email or settings.smtp_username
        self.smtp_from_name = settings.smtp_from_name
        
        # Initialize AWS SES client if configured
        self.ses_client = None
        if self.use_aws_ses:
            try:
                self.ses_client = boto3.client(
                    'ses',
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region_name=settings.aws_region
                )
                logger.info("AWS SES client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize AWS SES: {e}")

    def is_configured(self) -> bool:
        """Check if email service is properly configured"""
        if self.use_aws_ses:
            return bool(
                self.ses_client and
                self.ses_from_email
            )
        else:
            return bool(
                self.smtp_host and
                self.smtp_username and
                self.smtp_password and
                self.smtp_from_email
            )

    def is_kindle_email(self, email: str) -> bool:
        """Check if email is a valid Kindle email address"""
        kindle_domains = [
            "@kindle.com",
            "@free.kindle.com",
            "@kindle.cn",  # China
            "@free.kindle.cn",
        ]
        email_lower = email.lower()
        return any(email_lower.endswith(domain) for domain in kindle_domains)

    async def send_to_kindle(
        self,
        to_email: str,
        book_path: str,
        book_title: str,
        format: str = "MOBI"
    ) -> bool:
        """
        Send a book file to Kindle via email.
        
        Args:
            to_email: Kindle email address (e.g., user@kindle.com)
            book_path: Path to the book file
            book_title: Title of the book
            format: Book format (MOBI, EPUB, PDF, etc.)
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.error("Email service is not configured")
            return False

        if not self.is_kindle_email(to_email):
            logger.warning(f"Email {to_email} does not appear to be a Kindle email address")

        # Validate file exists
        if not Path(book_path).exists():
            logger.error(f"Book file not found: {book_path}")
            return False

        try:
            # Create message
            msg = MIMEMultipart()
            # Use appropriate from email based on service type
            if self.use_aws_ses:
                from_email = self.ses_from_email
                from_name = self.ses_from_name
            else:
                from_email = self.smtp_from_email
                from_name = self.smtp_from_name
            
            msg["From"] = f"{from_name} <{from_email}>"
            msg["To"] = to_email
            msg["Subject"] = book_title

            # Add body (optional - some users prefer empty body)
            body = f"Sent from {from_name}\n\nBook: {book_title}"
            msg.attach(MIMEText(body, "plain"))

            # Attach book file
            with open(book_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())

            # Encode file in ASCII characters to send by email
            encoders.encode_base64(part)

            # Determine filename
            # Kindle prefers simple filenames without special characters
            safe_title = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in book_title)
            safe_title = safe_title[:50]  # Limit length
            filename = f"{safe_title}.{format.lower()}"

            part.add_header(
                "Content-Disposition",
                "attachment",
                filename=filename,
            )

            msg.attach(part)

            # Send email via AWS SES or SMTP
            if self.use_aws_ses and self.ses_client:
                # Send via AWS SES (run in executor since boto3 is synchronous)
                try:
                    loop = asyncio.get_event_loop()
                    # AWS SES Source should be just the email, the name is in the message headers
                    response = await loop.run_in_executor(
                        None,
                        lambda: self.ses_client.send_raw_email(
                            Source=self.ses_from_email,
                            Destinations=[to_email],
                            RawMessage={'Data': msg.as_string()}
                        )
                    )
                    logger.info(f"AWS SES message ID: {response['MessageId']}")
                    logger.info(f"Successfully sent book '{book_title}' to {to_email} via AWS SES")
                    return True
                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                    error_msg = e.response.get('Error', {}).get('Message', str(e))
                    logger.error(f"AWS SES error ({error_code}): {error_msg}")
                    return False
                except Exception as e:
                    logger.error(f"AWS SES error: {e}")
                    return False
            else:
                # Send via SMTP (fallback if AWS SES not available)
                if not HAS_AIOSMTPLIB:
                    logger.error("SMTP sending requires aiosmtplib. Install it with: pip install aiosmtplib")
                    return False
                
                await aiosmtplib.send(
                    msg,
                    hostname=self.smtp_host,
                    port=self.smtp_port,
                    username=self.smtp_username,
                    password=self.smtp_password,
                    use_tls=self.smtp_use_tls,
                )
                logger.info(f"Successfully sent book '{book_title}' to {to_email}")
                return True

        except Exception as e:
            logger.error(f"Error sending email to Kindle: {e}")
            return False

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachments: Optional[List[tuple]] = None
    ) -> bool:
        """
        Send a general email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            attachments: List of tuples (file_path, filename)
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.error("Email service is not configured")
            return False

        try:
            msg = MIMEMultipart()
            # Use appropriate from email based on service type
            if self.use_aws_ses:
                from_email = self.ses_from_email
                from_name = self.ses_from_name
            else:
                from_email = self.smtp_from_email
                from_name = self.smtp_from_name
            
            msg["From"] = f"{from_name} <{from_email}>"
            msg["To"] = to_email
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "plain"))

            # Add attachments if provided
            if attachments:
                for file_path, filename in attachments:
                    if Path(file_path).exists():
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                "Content-Disposition",
                                "attachment",
                                filename=filename,
                            )
                            msg.attach(part)

            # Send email via AWS SES or SMTP
            if self.use_aws_ses and self.ses_client:
                # Send via AWS SES (run in executor since boto3 is synchronous)
                try:
                    loop = asyncio.get_event_loop()
                    # AWS SES Source should be just the email, the name is in the message headers
                    response = await loop.run_in_executor(
                        None,
                        lambda: self.ses_client.send_raw_email(
                            Source=self.ses_from_email,
                            Destinations=[to_email],
                            RawMessage={'Data': msg.as_string()}
                        )
                    )
                    logger.info(f"AWS SES message ID: {response['MessageId']}")
                    logger.info(f"Successfully sent email to {to_email} via AWS SES")
                    return True
                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                    error_msg = e.response.get('Error', {}).get('Message', str(e))
                    logger.error(f"AWS SES error ({error_code}): {error_msg}")
                    return False
                except Exception as e:
                    logger.error(f"AWS SES error: {e}")
                    return False
            else:
                # Send via SMTP (fallback if AWS SES not available)
                if not HAS_AIOSMTPLIB:
                    logger.error("SMTP sending requires aiosmtplib. Install it with: pip install aiosmtplib")
                    return False
                
                await aiosmtplib.send(
                    msg,
                    hostname=self.smtp_host,
                    port=self.smtp_port,
                    username=self.smtp_username,
                    password=self.smtp_password,
                    use_tls=self.smtp_use_tls,
                )
                logger.info(f"Successfully sent email to {to_email}")
                return True

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False


# Singleton instance
email_service = EmailService()

