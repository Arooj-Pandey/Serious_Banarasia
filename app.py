# App module to correctly expose the FastAPI app instance for Uvicorn
import sys
import os

# Add the project root directory to the path to ensure we import from main.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import app from main.py (not from main directory)
from main import app as app

# This file only exists to properly expose the app for uvicorn reload
# The app variable above is imported from main.py and made available at the module level

# Add this block to start the server when app.py is run directly
if __name__ == "__main__":
    import uvicorn
    
    # Use port 8080 as configured in main.py or override here
    port = int(os.getenv("PORT", 8000))
    print(f"Server will start on port: {port}")
    
    # Start the uvicorn server with optimized settings for production
    uvicorn.run(
        "app:app",  # Use the current module name and app variable
        host="0.0.0.0",
        port=port,
        workers=4,  # Multiple workers to handle concurrent requests
        timeout_keep_alive=120,  # Keep connections alive longer
        limit_concurrency=20,  # Limit concurrent connections to prevent overload
        timeout_graceful_shutdown=30,  # Grace period for shutdown
        reload=os.getenv("ENVIRONMENT", "production").lower() == "development"  # Only enable reload in development
    )