Crawl4ai-agent-mod
# Documentation Crawler Agent

A specialized AI agent that crawls and extracts documentation from websites, designed for the Live Agent Studio platform.

## Features

- Recursive web crawling with configurable depth and limits
- Smart documentation page detection
- Intelligent content chunking with preservation of:
  - Code blocks (with language detection)
  - Tables
  - Images
  - Math blocks
  - Blockquotes
- Fallback mechanism for documentation extraction
- Integration with Live Agent Studio's messaging system

## Setup

1. Set environment variables:
```bash
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the agent:
```bash
python src/api/agent_api.py
```

## Usage

Send a POST request to `/crawl` with:
```json
{
  "query": "Crawl documentation at https://example.com/docs",
  "user_id": "user123",
  "request_id": "req456",
  "session_id": "sess789"
}
```

The agent will:
1. Extract the URL from the query
2. Crawl the documentation
3. Store structured content in the database
4. Return a success/failure response

## Live Agent Studio Integration

This agent follows all Live Agent Studio requirements:
- Accepts standard input parameters
- Uses the messages table for conversation storage
- Returns standardized responses
- Handles errors gracefully

## Credit & Attribution

The Credit URL is a link that Live Agent Studio displays to users when they interact with your agent. This helps users:
- Learn more about you or your organization
- Find your other projects/work
- Contact you for questions or collaboration

You can use any of these as your Credit URL:
- GitHub profile/repository
- Organization website
- Personal website/portfolio
- LinkedIn profile
- Other professional presence

For this agent:
Created by: [Your Name/Organization]
Credit URL: [Your URL]



