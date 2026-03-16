from google.adk.agents import Agent
from tools.screenshot_tool import take_screenshot_tool
from tools.navigate_tool import navigate_tool
from tools.form_fill_tool import form_fill_tool, cover_letter_tool, mark_job_applied_tool, mark_job_skipped_tool
import os
from lib.gemini_helper import get_gemini_model

# Get resilient model for agent cognition
agent_model = get_gemini_model().model_name.replace("models/", "")

# Define the ADK Agent
resume_agent = Agent(
    name="ResumeApplyAgent",
    model=agent_model,
    description="""
    You are an autonomous Auto-Apply Agent. You control a real browser to find and apply to jobs on behalf of the user.
    
    CRITICAL INSTRUCTIONS:
    1. Start by navigating to https://www.linkedin.com/jobs or https://www.indeed.com/.
    2. USE take_screenshot_tool with a descriptive action_context (e.g. "Looking at homepage") to see what's on the screen.
    3. Use navigate_tool with action="click" and a selector_description (e.g. "Search bar") to focus inputs.
    4. Use navigate_tool with action="type" to enter the user's role and location preferences.
    5. After every significant action, TAKE ANOTHER SCREENSHOT to verify the page state.
    6. Click on job cards, look for 'Easy Apply' or 'Apply Now'.
    7. Use form_fill_tool if you encounter form fields.
    8. Once applied, report the successful application and loop to the next job.
    """,
    tools=[
        take_screenshot_tool,
        navigate_tool,
        form_fill_tool,
        cover_letter_tool,
        mark_job_applied_tool,
        mark_job_skipped_tool
    ]
)
