@echo off
echo Checking for existing Streamlit processes...

REM Kill any existing Streamlit processes with maximum force
taskkill /F /IM streamlit.exe /T 2>nul
taskkill /F /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq *Streamlit*" 2>nul

echo Starting Ronan AI Valet...

REM Start Streamlit
start /B streamlit run app/streamlit_app.py --server.port 8053 > streamlit.log 2>&1

echo Ronan is running on http://localhost:8053
echo Press Ctrl+C to exit...

:WAIT_FOR_EXIT
timeout /t 1 /nobreak >nul
REM Check if user pressed Ctrl+C
if errorlevel 1 goto CLEANUP
goto WAIT_FOR_EXIT

:CLEANUP
echo.
echo Shutting down Ronan...
REM Kill with /T flag to terminate tree of processes
taskkill /F /IM streamlit.exe /T 2>nul
del streamlit.log 2>nul
echo Goodbye!
exit /B 0 