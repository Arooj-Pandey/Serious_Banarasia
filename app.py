# App module to correctly expose the FastAPI app instance for Uvicorn
import sys
import os

# Add the project root directory to the path to ensure we import from main.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import app from main.py (not from main directory)
from main import app as app
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Ensure static directory exists
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
    print(f"Created static directory at: {static_dir}")

# Mount static directory for serving images with improved caching settings
app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")

# Configure CORS with explicit frontend origin to ensure image loading works
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Type"],  # Important for file/image downloads
)

# Import the image attachment middleware
try:
    from middleware.response_formatter import ImageAttachmentMiddleware
    # Add middleware to process image URLs in responses
    app.add_middleware(ImageAttachmentMiddleware)
    print("Image attachment middleware enabled")
except ImportError:
    print("Warning: Could not load image attachment middleware - ensure directory structure is correct")

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