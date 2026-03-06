"""
WSGI entry point for production deployment with Gunicorn
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Import Flask app
from app import app as application

if __name__ == "__main__":
    # For local testing
    port = int(os.environ.get("PORT", 8000))
    application.run(host="0.0.0.0", port=port)
