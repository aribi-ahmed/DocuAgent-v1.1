import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GEMINI_API_KEY = os.getenv("API_KEY")
    JIRA_URL = os.getenv("JIRA_URL")
    CONFLUENCE_URL = os.getenv("CONFLUENCE_URL")