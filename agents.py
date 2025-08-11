# crewai_app/agents.py
import os
from crewai import Agent, LLM
from dotenv import load_dotenv
from crewai_app.tools import file_reader, email_extractor, name_extractor, email_sender

load_dotenv()


def get_gemini_llm():
    """Get configured Gemini LLM instance with error handling"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("WARNING: GEMINI_API_KEY not found in environment variables")
        raise ValueError("GEMINI_API_KEY not found in environment variables")

    print(f"DEBUG: Using Gemini API Key (first 10 chars): {api_key[:10]}...")

    # Try different model configurations
    try:
        # Option 1: Standard Gemini configuration
        print("DEBUG: Trying gemini/gemini-2.5-flash configuration...")
        llm = LLM(
            model="gemini/gemini-2.5-flash-preview-05-20",
            api_key=api_key,
            temperature=0.7
        )
        print("DEBUG: Successfully configured gemini/gemini-2.5-flash-preview-05-20")
        return llm
    except Exception as e:
        print(f"DEBUG: gemini/gemini-2.5-flash-preview-05-20 failed: {e}")
        try:
            # Option 2: Alternative configuration
            print("DEBUG: Trying gemini-2.5-flash-preview-05-20...")
            llm = LLM(
                model="gemini-2.5-flash-preview-05-20",
                api_key=api_key,
                temperature=0.7
            )
            print("DEBUG: Successfully configured gemini-2.5-flash-preview-05-20")
            return llm
        except Exception as e2:
            print(f"DEBUG: gemini-2.5-flash-preview-05-20: {e2}")
            try:
                # Option 3: Another alternative
                print(
                    "DEBUG: Trying google/gemini-2.5-flash-preview-05-20 configuration...")
                llm = LLM(
                    model="google/gemini-2.5-flash-preview-05-20",
                    api_key=api_key,
                    temperature=0.7
                )
                print(
                    "DEBUG: Successfully configured google/gemini-2.5-flash-preview-05-20")
                return llm
            except Exception as e3:
                print(f"DEBUG: google/gemini-2.5-flash-preview-05-20: {e3}")
                # Fallback to a simple configuration
                print("DEBUG: Trying simple gemini-pro configuration...")
                llm = LLM(
                    model="gemini-2.5-flash-preview-05-20",
                    api_key=api_key
                )
                print("DEBUG: Successfully configured")
                return llm


class RecruitmentAgents:
    def __init__(self):
        try:
            print("DEBUG: Initializing RecruitmentAgents...")
            self.llm = get_gemini_llm()
            print("DEBUG: LLM configured successfully!")
        except Exception as e:
            print(f"ERROR: Failed to initialize LLM: {e}")
            # Create a dummy LLM to prevent crashes during development
            self.llm = None
            raise

    def resume_screener_agent(self):
        if not self.llm:
            raise ValueError("LLM not properly configured")

        return Agent(
            role="Senior AI Recruiter",
            goal="Extract and analyze resume content accurately from uploaded files",
            backstory="""You are an experienced recruiter with expertise in reading and analyzing 
            resumes from various formats including PDF, DOCX, and TXT files. You have a keen eye 
            for extracting relevant information and understanding candidate profiles.""",
            llm=self.llm,
            tools=[file_reader],
            verbose=True,
            allow_delegation=False
        )

    def resume_reader_agent(self):
        """Alias for backward compatibility"""
        return self.resume_screener_agent()

    def contact_extractor_agent(self):
        if not self.llm:
            raise ValueError("LLM not properly configured")

        return Agent(
            role="Contact Information Specialist",
            goal="Extract contact information including email and name from resume text",
            backstory="""You specialize in finding and extracting contact details from candidate 
            resumes. You have expertise in parsing text to identify email addresses and candidate 
            names accurately.""",
            llm=self.llm,
            tools=[email_extractor, name_extractor],
            verbose=True,
            allow_delegation=False
        )

    def communication_agent(self):
        if not self.llm:
            raise ValueError("LLM not properly configured")

        return Agent(
            role="HR Communication Specialist",
            goal="Send professional interview invitation emails to qualified candidates",
            backstory="""You are responsible for sending professional and engaging interview 
            invitations to qualified candidates. You ensure all communications maintain a 
            professional tone while being welcoming and informative.""",
            llm=self.llm,
            tools=[email_sender],
            verbose=True,
            allow_delegation=False
        )

    def email_sender_agent(self):
        """Alias for communication agent"""
        return self.communication_agent()

    def scoring_agent(self):
        if not self.llm:
            raise ValueError("LLM not properly configured")

        return Agent(
            role="Resume Scoring Specialist",
            goal="Score resumes based on job requirements and candidate qualifications",
            backstory="""You are an expert at evaluating candidates against job requirements. 
            You analyze resumes and provide scores based on skills match, experience relevance, 
            and overall fit for the position.""",
            llm=self.llm,
            tools=[],
            verbose=True,
            allow_delegation=False
        )

    def interview_scheduler_agent(self):
        """Interview scheduler agent for coordinating candidate interviews"""
        if not self.llm:
            raise ValueError("LLM not properly configured")

        return Agent(
            role="Interview Scheduler",
            goal="Schedule interviews with qualified candidates efficiently and professionally",
            backstory="""You are an experienced HR coordinator who specializes in interview scheduling.
            You understand the importance of coordinating between candidates, interviewers, and HR teams
            to ensure smooth interview processes. You're skilled at finding optimal time slots,
            sending professional communications, and managing interview logistics.""",
            llm=self.llm,
            tools=[],  # Add any scheduling tools if needed
            verbose=True,
            allow_delegation=False
        )
