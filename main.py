import os
import shutil
import re
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import google.generativeai as genai
from fastapi.middleware.cors import CORSMiddleware

from crewai import Crew, Process
from crewai_app.agents import RecruitmentAgents
from crewai_app.tasks import RecruitmentTasks

# Load environment variables from .env file
load_dotenv()

# Retrieve the Gemini API key from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    print(f"DEBUG: Loaded API Key (first 5 chars): {GEMINI_API_KEY[:5]}...")
else:
    print("DEBUG: GEMINI_API_KEY not found in environment variables. Please set it in your .env file.")

# Configure the Gemini API globally for the application
genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI(
    title="CrewAI Recruitment Assistant API",
    description="API for AI-powered resume screening and automated interview scheduling using CrewAI.",
    version="1.0.0"
)

# CORS middleware for frontend-backend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure the upload directory exists


def save_uploaded_file(upload_file: UploadFile, upload_folder: str = UPLOAD_FOLDER) -> str:
    """Saves an uploaded file to the specified folder and returns its path."""
    file_path = os.path.join(upload_folder, upload_file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        print(f"File '{upload_file.filename}' saved to '{file_path}'")
        return file_path
    except Exception as e:
        print(f"Error saving file {upload_file.filename}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Could not save uploaded file: {e}")


def extract_task_output_text(task_output):
    """
    Helper function to extract text from CrewAI TaskOutput object.
    TaskOutput objects have different attributes depending on the version.
    """
    if task_output is None:
        return ""

    # Try different possible attributes for task output text
    if hasattr(task_output, 'raw'):
        return str(task_output.raw)
    elif hasattr(task_output, 'result'):
        return str(task_output.result)
    elif hasattr(task_output, 'output'):
        return str(task_output.output)
    elif hasattr(task_output, 'content'):
        return str(task_output.content)
    else:
        # Fallback: convert the entire object to string
        return str(task_output)


@app.post("/process_resume/")
async def process_resume(
    resume_file: UploadFile = File(...),
    job_description: str = "SDE",
    min_score_for_interview: int = 60
):
    """
    Processes an uploaded resume through a CrewAI workflow:
    - Reads the resume text.
    - Screens the resume using an AI recruiter agent.
    - If suitable, the AI scheduler agent extracts contact info and sends an interview invitation email.
    """
    file_path = None  # Initialize to None
    try:
        # 1. Save the uploaded file temporarily
        file_path = save_uploaded_file(resume_file)

        # 2. Initialize CrewAI components
        agents = RecruitmentAgents()
        tasks = RecruitmentTasks()

        # Instantiate agents
        screener_agent = agents.resume_screener_agent()
        scheduler_agent = agents.interview_scheduler_agent()

        # Define tasks for the crew in sequential order
        # Task 1: Read the resume file
        read_task = tasks.read_resume_task(screener_agent, file_path)

        # Task 2: Screen the resume (using the output of read_task as input)
        screen_task = tasks.screen_resume_task(
            screener_agent, read_task.output, job_description)

        # Task 3: Decide whether to schedule and, if so, send the email
        decide_and_schedule_task = tasks.decide_and_schedule_task(
            scheduler_agent,
            screen_task.output,
            read_task.output,
            job_description,
            min_score_for_interview
        )

        # 3. Form the Crew
        recruitment_crew = Crew(
            agents=[screener_agent, scheduler_agent],
            tasks=[read_task, screen_task, decide_and_schedule_task],
            verbose=True,  # Set to True for detailed logging of agent thoughts and actions
            process=Process.sequential  # Tasks run in the order defined
        )

        # 4. Kick off the Crew's work
        print("\n### Starting Recruitment Workflow ###")
        crew_result = recruitment_crew.kickoff()
        print("\n### Recruitment Workflow Completed ###")

        # 5. Extract relevant information from task outputs for the API response
        try:
            # The screen_task.output contains the full evaluation text
            screening_result_text = extract_task_output_text(
                screen_task.output)
            print(f"DEBUG: Screening result type: {type(screen_task.output)}")
            print(
                f"DEBUG: Screening result preview: {screening_result_text[:200]}...")

            suitability_score = 0
            score_match = re.search(
                r"Suitability Score:\s*(\d+)/100", screening_result_text)
            if score_match:
                suitability_score = int(score_match.group(1))
            else:
                # Try alternative patterns
                alt_patterns = [
                    r"Score:\s*(\d+)/100",
                    r"(\d+)/100",
                    r"Score:\s*(\d+)%",
                    r"(\d+)%"
                ]
                for pattern in alt_patterns:
                    score_match = re.search(pattern, screening_result_text)
                    if score_match:
                        suitability_score = int(score_match.group(1))
                        break

            # The final task output from decide_and_schedule_task summarizes the email action
            scheduling_summary = extract_task_output_text(
                decide_and_schedule_task.output)

            print(f"DEBUG: Scheduling summary: {scheduling_summary}")

        except Exception as extraction_error:
            print(f"Error extracting task outputs: {extraction_error}")
            # Provide fallback values
            screening_result_text = str(
                screen_task.output) if screen_task.output else "Error extracting screening result"
            scheduling_summary = str(
                decide_and_schedule_task.output) if decide_and_schedule_task.output else "Error extracting scheduling summary"
            suitability_score = 0

        # Determine if email was sent from the summary
        email_sent_status = "unknown"
        if "Interview invitation sent to" in scheduling_summary:
            email_sent_status = "sent"
        elif "Interview not scheduled" in scheduling_summary:
            email_sent_status = "not_sent_insufficient_score"
        elif "Failed to send interview invitation" in scheduling_summary:
            email_sent_status = "not_sent_email_error"
        elif "✅" in scheduling_summary:
            email_sent_status = "sent"
        elif "❌" in scheduling_summary:
            email_sent_status = "not_sent_email_error"

        return JSONResponse(content={
            "status": "workflow_completed",
            "message": "Resume processing workflow executed by CrewAI.",
            "job_description": job_description,
            "min_score_threshold": min_score_for_interview,
            "screening_result": screening_result_text,
            "suitability_score": suitability_score,
            "scheduling_summary": scheduling_summary,
            "email_sending_status": email_sent_status,
            "crew_execution_log": str(crew_result)
        })

    except HTTPException as e:
        # Re-raise HTTPExceptions directly, as they are controlled errors
        raise e
    except Exception as e:
        print(f"An unexpected error occurred during CrewAI execution: {e}")
        import traceback
        traceback.print_exc()  # Print full traceback for server-side debugging
        raise HTTPException(
            status_code=500, detail=f"An internal server error occurred: {str(e)}")
    finally:
        # Ensure the temporarily saved file is removed regardless of success or failure
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            print(f"Cleaned up temporary file: {file_path}")


@app.get("/")
async def root():
    return {"message": "Welcome to the CrewAI Recruitment Assistant API. Use /docs for API documentation."}


@app.post("/chat/")
async def chat_with_gemini(message: dict):
    """
    Allows a user to chat with the Gemini AI model directly.
    Expects a JSON body like {"message": "Hello"}.
    """
    user_message = message.get("message")
    if not user_message:
        raise HTTPException(
            status_code=400, detail="Message not provided in request body.")

    try:
        prompt = f"User: {user_message}\nAI:"

        model = genai.GenerativeModel("models/gemini-2.0-flash")
        response = model.generate_content(prompt)
        return JSONResponse(content={"response": response.text})
    except Exception as e:
        print(f"Error during chat: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error during chat: {str(e)}")
