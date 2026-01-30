import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv() 

# Key is now accessible via os.environ.get("OPENAI_API_KEY")
api_key = os.environ.get("OPENAI_API_KEY")