# MyAiStaffSwarm

An AI agent swarm system that coordinates multiple AI agents to work together on complex tasks. Built with modern Python, FastAPI, and integrated with various LLM models through Ollama.

## Features

- Multi-agent coordination and communication
- Integration with Ollama for local LLM support
- Supabase database integration
- Streamlit and Chainlit web interfaces
- Modular agent architecture
- Protected document handling
- Comprehensive logging system

## Environment Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables in `.env`:
```bash
# Create a .env file with your configuration
# See .env.example for required variables
```

3. Initialize Ollama (Windows):
```powershell
./init_ollama.bat
```

## Running the Application

### Development Mode
```powershell
./run_dev.ps1
```

### Streamlit Interface
```powershell
./run_streamlit.ps1
```

## Project Structure

- `/app` - Core application code
- `/src` - Source code for agents and utilities
- `/tools` - Custom tool implementations
- `/tests` - Test suite
- `/protected_docs` - Secure document storage
- `/logs` - Application logs

## Development

This project uses:
- Python 3.11+
- FastAPI for API endpoints
- Pydantic for data validation
- Supabase for database
- Ollama for LLM integration
- Streamlit/Chainlit for UI

## Testing

```bash
pytest tests/
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Your chosen license]



