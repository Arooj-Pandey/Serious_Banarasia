# App module to correctly expose the FastAPI app instance for Uvicorn
import sys
import os

# Add the project root directory to the path to ensure we import from main.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import app from main.py (not from main directory)
from main import app as app

# This file only exists to properly expose the app for uvicorn reload
# The app variable above is imported from main.py and made available at the module level