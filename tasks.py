# crewai_app/tasks.py
from crewai import Task
from crewai_app.tools import file_reader, email_extractor, name_extractor, email_sender
import re  # For parsing the score
import os


class RecruitmentTasks:
    def read_resume_task(self, agent, file_path: str):
        return Task(
            description=f"Read the content of the resume located at {file_path}. Ensure all text is extracted.",
            expected_output="The full plain text content of the resume.",
            agent=agent,
            # Ensure file_reader is available to the agent via its tools list
            tools=[file_reader],
            human_input=False
        )

    def screen_resume_task(self, agent, resume_text: str, job_description: str):
        return Task(
            description=f"""
                Evaluate the following resume text against the job description for a '{job_description}' role.
                Provide a suitability score from 0 to 100, a brief explanation, and recommended next steps.
                The output MUST clearly state 'Suitability Score: XX/100' on a new line for easy parsing.
                Resume:
                {resume_text}
            """,
            expected_output="A comprehensive evaluation including 'Suitability Score: XX/100', explanation, and next steps.",
            agent=agent,
            human_input=False
        )

    def decide_and_schedule_task(self, agent, screening_result: str, resume_text: str, job_description: str, min_score_for_interview: int):

        return Task(
            description=f"""
                Analyze the provided resume screening result:
                ---
                {screening_result}
                ---

                Based on this result, you must parse the 'Suitability Score' and determine if it is {min_score_for_interview} or higher.
                
                If the score is {min_score_for_interview} or higher:
                1. Use the 'Email Extraction Tool' on the provided original resume text to get the candidate's email.
                2. Use the 'Name Extraction Tool' on the provided original resume text to get the candidate's name.
                3. Use the 'Email Sending Tool' to send an interview invitation email.
                   - The 'recipient_email' should be the extracted email.
                   - The 'candidate_name' should be the extracted name.
                   - The 'role_name' should be '{job_description}'.
                   - The tool will print success/failure, which you should confirm.
                4. Conclude your final answer by stating 'Interview invitation sent to [email]' if successful, or 'Failed to send interview invitation: [reason]' if unsuccessful.

                If the score is below {min_score_for_interview}:
                1. Do NOT send an interview invitation.
                2. Conclude your final answer by stating 'Interview not scheduled due to insufficient suitability score.'
                
                Original Resume Text (for email/name extraction, if needed):
                ---
                {resume_text}
                ---
            """,
            expected_output="A concise summary of the decision (scheduled/not scheduled) and the outcome of the email sending, clearly stating the email if sent.",
            agent=agent,
            # Ensure the agent has access to all tools needed for this task
            tools=[email_extractor, name_extractor, email_sender],
            human_input=False
        )
