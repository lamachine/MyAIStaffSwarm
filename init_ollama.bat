@echo off
echo Initializing Ollama with GPU settings...

REM Stop any running Ollama instance
taskkill /F /IM ollama.exe 2>nul

REM Pull the model with GPU configuration
ollama pull llama3.1:latest

REM Create a custom model with GPU settings
echo Creating GPU-enabled model...
(
echo FROM llama3.1:latest
echo PARAMETER num_gpu 44
echo PARAMETER num_thread 8
echo PARAMETER cuda true
echo PARAMETER mmap true
) > modelfile

ollama create llama3.1-gpu -f modelfile

echo Ollama initialized with GPU support
echo Starting Ollama service...
start /B ollama serve
timeout /t 5 