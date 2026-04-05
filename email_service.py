import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from io import BytesIO
from datetime import datetime
from dotenv import load_dotenv
import re

load_dotenv()

class EmailService:
    """Email service for sending notes via email"""
    
    def __init__(self):
        # Unifying with .env names
        self.sender_email = os.environ.get('SMTP_EMAIL', os.environ.get('EMAIL_SENDER', ''))
        self.sender_password = os.environ.get('SMTP_PASSWORD', os.environ.get('EMAIL_PASSWORD', ''))
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', 587))
        self.is_configured = bool(self.sender_email and self.sender_password)
    
    def send_notes_email(
        self,
        recipient_email: str,
        subject: str,
        notes_content: str,
        sender_name: str = "EchoMind",
        attachment_bytes: BytesIO = None,
        attachment_filename: str = None,
        attachment_mime: str = "application/pdf"
    ) -> tuple:
        """
        Send notes via email.
        Returns (success: bool, message: str)
        """
        if not self.is_configured:
            return False, "Email service is not configured. Please set SMTP_EMAIL and SMTP_PASSWORD in your .env file."
        
        if not recipient_email or '@' not in recipient_email:
            return False, "Please enter a valid email address."
        
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{sender_name} <{self.sender_email}>"
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            # Plain text version
            plain_text = self._markdown_to_plain_text(notes_content)
            text_part = MIMEText(plain_text, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # HTML version
            html_content = self._markdown_to_html(notes_content, sender_name)
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Attachment
            if attachment_bytes and attachment_filename:
                attachment_bytes.seek(0)
                attachment_data = attachment_bytes.read()
                
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment_data)
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{attachment_filename}"'
                )
                msg.attach(part)
            
            # Send
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            return True, f"Notes sent successfully to {recipient_email}!"
        
        except smtplib.SMTPAuthenticationError:
            return False, ("Email authentication failed. If using Gmail, make sure you're using an App Password. "
                          "Go to Google Account > Security > 2-Step Verification > App Passwords")
        except smtplib.SMTPRecipientsRefused:
            return False, f"The recipient email '{recipient_email}' was rejected."
        except smtplib.SMTPException as e:
            return False, f"SMTP error: {str(e)}"
        except ConnectionRefusedError:
            return False, "Could not connect to email server. Check SMTP settings."
        except Exception as e:
            return False, f"Failed to send email: {str(e)}"
    
    def _markdown_to_plain_text(self, markdown_content: str) -> str:
        text = markdown_content
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        text = re.sub(r'^-{3,}$', '\n' + '='*50 + '\n', text, flags=re.MULTILINE)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        return text
    
    def _markdown_to_html(self, markdown_content: str, sender_name: str = "EchoMind") -> str:
        html = markdown_content
        
        # Convert headers
        html = re.sub(r'^###\s+(.+)$', r'<h3 style="color: #4f46e5; margin: 20px 0 10px 0; font-size: 18px;">\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^##\s+(.+)$', r'<h2 style="color: #2b5876; margin: 25px 0 12px 0; font-size: 22px; border-bottom: 2px solid #e0c3fc; padding-bottom: 8px;">\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^#\s+(.+)$', r'<h1 style="color: #2b5876; margin: 30px 0 15px 0; font-size: 26px;">\1</h1>', html, flags=re.MULTILINE)
        
        # Bold and italic
        html = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', html)
        
        # Bullet points
        html = re.sub(r'^\s*[-*+]\s+(.+)$', r'<li style="margin: 5px 0; color: #333;">\1</li>', html, flags=re.MULTILINE)
        
        # Horizontal rules
        html = re.sub(r'^-{3,}$', '<hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;">', html, flags=re.MULTILINE)
        
        # Line breaks
        html = html.replace('\n\n', '</p><p style="margin: 10px 0; color: #333; line-height: 1.6;">')
        html = html.replace('\n', '<br>')
        
        current_date = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
        <body style="margin: 0; padding: 0; background-color: #f4f0ff; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
            <div style="max-width: 700px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 16px 16px 0 0; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 28px;">🧠 {sender_name}</h1>
                    <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0; font-size: 14px;">Intelligent Note Generation</p>
                </div>
                <div style="background-color: white; padding: 30px; border: 1px solid #e0e0e0;">
                    <p style="color: #666; font-size: 13px; margin-bottom: 20px;">Generated on {current_date}</p>
                    <div style="color: #333; line-height: 1.6;">
                        <p style="margin: 10px 0; color: #333; line-height: 1.6;">{html}</p>
                    </div>
                </div>
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 0 0 16px 16px; text-align: center; border: 1px solid #e0e0e0; border-top: none;">
                    <p style="color: #888; font-size: 12px; margin: 0;">
                        Generated by {sender_name} | MIT ADT University, Pune<br>
                        Created by Pratik Dalvi, Sushant Marathe, Abhinav Anand, Sushmita Shinde
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        return full_html
    
    def get_status(self) -> dict:
        return {
            'configured': self.is_configured,
            'server': self.smtp_server,
            'port': self.smtp_port,
            'sender': self.sender_email if self.is_configured else 'Not configured'
        }