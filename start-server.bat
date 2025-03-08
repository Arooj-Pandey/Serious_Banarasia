@echo off
:: Set environment variables
set PORT=8000
set ENVIRONMENT=production

:: Activate virtual environment if it exists
if exist myenv\Scripts\activate.bat (
  echo Activating virtual environment...
  call myenv\Scripts\activate.bat
)

:: Install dependencies if needed
if "%1"=="--install" (
  echo Installing dependencies...
  pip install -r requirements.txt
)

:: Start the server with optimized settings for production
echo Starting Varanasi Chatbot API server...
uvicorn app:app --host 0.0.0.0 --port %PORT% --workers 4 --timeout-keep-alive 120 --limit-concurrency 20 --timeout-graceful-shutdown 30

:: This script can be run with:
:: start-server.bat
:: or to install dependencies:
:: start-server.bat --install