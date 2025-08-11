import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from typing import Optional
from PyPDF2 import PdfReader
from docx import Document
import traceback

try:
    from crewai_tools import BaseTool
    Tool = BaseTool
except ImportError:
    try:
        from crewai.tools import BaseTool
        Tool = BaseTool
    except ImportError:
        try:
            from crewai import Tool
        except ImportError:
            class Tool:
                def __init__(self):
                    pass

                def run(self, *args, **kwargs):
                    return self._run(*args, **kwargs)

                def _run(self, *args, **kwargs):
                    raise NotImplementedError(
                        "Subclasses must implement _run method")

from dotenv import load_dotenv
load_dotenv()

# Environment variables with debug output
print("🔍 LOADING ENVIRONMENT VARIABLES...")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
HR_EMAIL_SENDER = os.getenv("HR_EMAIL_SENDER", "hr@nxtwave.com")
COMPANY_NAME = os.getenv("COMPANY_NAME", "nxtWave")
COMPANY_WEBSITE = os.getenv("COMPANY_WEBSITE", "https://www.ccbp.in/")
INTERVIEW_RESPONSE_DAYS = int(os.getenv("INTERVIEW_RESPONSE_DAYS", 2))
EMAIL_TEST_MODE = os.getenv("EMAIL_TEST_MODE", "false").lower() == "true"
print(
    f"DEBUG: EMAIL_TEST_MODE loaded as: {EMAIL_TEST_MODE} (type: {type(EMAIL_TEST_MODE)})")

print(f"✅ Environment loaded - Test Mode: {EMAIL_TEST_MODE}")


class FileReadingTool(Tool):
    """A tool to read content from PDF, DOCX, or TXT files."""
    name: str = "File Reading Tool"
    description: str = "A tool to read content from PDF, DOCX, or TXT files. Input is the file path."

    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text() or ""
        except Exception as e:
            print(f"Error extracting text from PDF {pdf_path}: {e}")
            raise
        return text

    def _extract_text_from_docx(self, docx_path: str) -> str:
        full_text = []
        try:
            document = Document(docx_path)
            for para in document.paragraphs:
                full_text.append(para.text)
        except Exception as e:
            print(f"Error extracting text from DOCX {docx_path}: {e}")
            raise
        return '\n'.join(full_text)

    def _extract_text_from_txt(self, txt_path: str) -> str:
        try:
            with open(txt_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"Error extracting text from TXT {txt_path}: {e}")
            raise

    def _run(self, file_path: str) -> str:
        """Main method for the tool to be called by agents."""
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension == '.pdf':
            return self._extract_text_from_pdf(file_path)
        elif file_extension == '.docx':
            return self._extract_text_from_docx(file_path)
        elif file_extension == '.txt':
            return self._extract_text_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")


class EmailExtractionTool(Tool):
    """A tool to extract the primary email address from a given text."""
    name: str = "Email Extraction Tool"
    description: str = "A tool to extract the primary email address from a given text."

    def _run(self, text: str) -> Optional[str]:
        """Main method for the tool to be called by agents."""
        email_regex = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
        emails = re.findall(email_regex, text)
        return emails[0] if emails else None


class NameExtractionTool(Tool):
    """A basic tool to extract the candidate's name from resume text."""
    name: str = "Name Extraction Tool"
    description: str = "A basic tool to extract the candidate's name from resume text."

    def _run(self, text: str) -> str:
        """Main method for the tool to be called by agents."""
        lines = text.strip().split('\n')
        if lines:
            first_line = lines[0].strip()
            if len(first_line.split()) < 5 and any(c.isalpha() for c in first_line):
                return first_line.title()
        return "Candidate"


class EmailSendingTool(Tool):
    """A tool to send professional interview invitation emails with comprehensive debugging."""
    name: str = "Email Sending Tool"
    description: str = "A tool to send professional interview invitation emails."

    def __init__(self):
        super().__init__()
        print(f"📧 EmailSendingTool initialized - Test Mode: {EMAIL_TEST_MODE}")

    def _run(self, recipient_email: str, candidate_name: str, role_name: str) -> bool:
        """Main method for the tool to be called by agents."""

        print(f"\n{'='*60}")
        print(f"📧 EMAIL SENDING ATTEMPT")
        print(f"{'='*60}")
        print(f"To: {recipient_email}")
        print(f"Candidate: {candidate_name}")
        print(f"Role: {role_name}")
        print(f"Test Mode: {EMAIL_TEST_MODE}")
        print(f"{'='*60}")

        try:
            # TEST MODE - Always succeeds
            if EMAIL_TEST_MODE:
                print("🧪 TEST MODE ACTIVE")
                print("✅ Email sending simulated successfully!")
                print(
                    f"📧 Subject: Interview Invitation: {role_name} Role at {COMPANY_NAME}")
                print(f"📬 To: {candidate_name} <{recipient_email}>")
                print(f"🏢 From: {HR_EMAIL_SENDER}")
                print(
                    f"⏰ Response expected: {INTERVIEW_RESPONSE_DAYS} business days")
                print(f"🌐 Company: {COMPANY_NAME} ({COMPANY_WEBSITE})")
                print("✅ EMAIL SENDING SUCCESSFUL (TEST MODE)")
                return True

            # PRODUCTION MODE - Real email sending
            print("🚀 PRODUCTION MODE - Attempting real email send")

            # Validate inputs
            if not recipient_email or '@' not in recipient_email:
                print(f"❌ Invalid email: {recipient_email}")
                return False

            if not candidate_name:
                print("❌ Missing candidate name")
                return False

            if not role_name:
                print("❌ Missing role name")
                return False

            # Check credentials
            if not SMTP_USERNAME or not SMTP_PASSWORD:
                print("❌ Missing SMTP credentials")
                print(f"Username: {'✅' if SMTP_USERNAME else '❌'}")
                print(f"Password: {'✅' if SMTP_PASSWORD else '❌'}")
                print("💡 Set EMAIL_TEST_MODE=true in .env for testing")
                return False

            # Create email content
            subject = f"Interview Invitation: {role_name} Role at {COMPANY_NAME}"

            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50;">🎉 Interview Invitation</h2>
                    
                    <p>Dear <strong>{candidate_name}</strong>,</p>
                    
                    <p>Thank you for your application for the <strong>{role_name}</strong> position at {COMPANY_NAME}. 
                    We've reviewed your profile and are impressed with your qualifications.</p>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; margin: 20px 0;">
                        <p><strong>We would like to invite you for an interview!</strong></p>
                    </div>
                    
                    <h3 style="color: #495057;">Next Steps:</h3>
                    <ul>
                        <li>Our HR team will contact you within <strong>{INTERVIEW_RESPONSE_DAYS} business days</strong></li>
                        <li>We'll schedule a convenient interview time</li>
                        <li>The interview will last approximately 45-60 minutes</li>
                    </ul>
                    
                    <p>Please confirm your continued interest by replying to this email.</p>
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6;">
                        <p><strong>Best regards,</strong><br>
                        The Recruitment Team<br>
                        <strong>{COMPANY_NAME}</strong><br>
                        <a href="{COMPANY_WEBSITE}">{COMPANY_WEBSITE}</a></p>
                    </div>
                </div>
            </body>
            </html>
            """

            plain_body = f"""
Dear {candidate_name},

Thank you for your application for the {role_name} position at {COMPANY_NAME}. 
We would like to invite you for an interview.

Our HR team will contact you within {INTERVIEW_RESPONSE_DAYS} business days.

Best regards,
The Recruitment Team
{COMPANY_NAME}
{COMPANY_WEBSITE}
            """

            # Send email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = HR_EMAIL_SENDER
            msg['To'] = recipient_email

            part1 = MIMEText(plain_body, 'plain')
            part2 = MIMEText(html_body, 'html')
            msg.attach(part1)
            msg.attach(part2)

            print(f"🔗 Connecting to {SMTP_SERVER}:{SMTP_PORT}")

            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)

            print("✅ EMAIL SENT SUCCESSFULLY!")
            return True

        except Exception as e:
            print(f"❌ EMAIL SENDING FAILED")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {str(e)}")
            print(f"Full Traceback:")
            traceback.print_exc()
            return False


# Tool instances with debugging
print("🔧 Creating tool instances...")
file_reader = FileReadingTool()
email_extractor = EmailExtractionTool()
name_extractor = NameExtractionTool()
email_sender = EmailSendingTool()
print("✅ All tools created successfully")

# Debug function


def debug_email_tool():
    """Debug the email tool directly"""
    print("\n🔍 DEBUGGING EMAIL TOOL DIRECTLY")
    print("="*50)

    result = email_sender._run(
        recipient_email="test@example.com",
        candidate_name="Test Candidate",
        role_name="Test Role"
    )

    print(f"\n📊 Result: {result}")
    print(f"📊 Type: {type(result)}")
    return result

# Test configuration


def test_config():
    """Test current configuration"""
    print("\n📋 CURRENT CONFIGURATION")
    print("="*40)
    print(f"SMTP_SERVER: {SMTP_SERVER}")
    print(f"SMTP_PORT: {SMTP_PORT}")
    print(f"SMTP_USERNAME: {SMTP_USERNAME}")
    print(
        f"SMTP_PASSWORD: {'*' * len(SMTP_PASSWORD) if SMTP_PASSWORD else '(empty)'}")
    print(f"EMAIL_TEST_MODE: {EMAIL_TEST_MODE}")
    print(f"HR_EMAIL_SENDER: {HR_EMAIL_SENDER}")
    print(f"COMPANY_NAME: {COMPANY_NAME}")
    print(f"COMPANY_WEBSITE: {COMPANY_WEBSITE}")
    print(f"INTERVIEW_RESPONSE_DAYS: {INTERVIEW_RESPONSE_DAYS}")


if __name__ == "__main__":
    test_config()
    debug_email_tool()
