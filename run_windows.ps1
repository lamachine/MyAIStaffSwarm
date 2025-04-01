# Set PYTHONPATH to the current directory
$env:PYTHONPATH = (Get-Location)

# Set Chainlit port
$env:CHAINLIT_PORT = "8083"

# Run the chainlit command
chainlit run app/chat.py -w 