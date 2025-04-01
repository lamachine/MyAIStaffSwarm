#!/bin/bash
set -e

echo "=== Startup Script Running ==="

# 1. Check/Start Tunnel Host (cloudflared)
# Replace "mytunnel" with your tunnel's name if needed.
echo "Checking for cloudflared tunnel..."
if ! pgrep -f "cloudflared tunnel run" >/dev/null 2>&1; then
    echo "Cloudflared tunnel not running. Starting tunnel..."
    # Run cloudflared in background.
    cloudflared tunnel run mytunnel &
    sleep 3  # Allow some time for the tunnel to initialize.
else
    echo "Cloudflared tunnel already running."
fi

# 2. Check Ollama service (listening on port 11434)
echo "Checking Ollama service on port 11434..."
if curl --silent --fail http://localhost:11434 >/dev/null 2>&1; then
    echo "Ollama service is running."
else
    echo "Ollama service is not responding. Please start Ollama manually."
fi

# 3. Verify required Docker containers

# For WSL, convert Windows paths to Linux paths.
DEV_STACK_COMPOSE="/mnt/c/Users/Owner/dev/Dev_docker_stack/dev_stack/docker-compose.yml"
SUPABASE_COMPOSE="/mnt/c/Users/Owner/dev/Dev_docker_stack/supabase/docker/docker-compose.yml"

echo "Checking Docker containers..."

# Check dev_stack container using docker compose ls
if docker compose ls | grep -q "dev_stack.*running"; then
    echo "dev_stack is running."
else
    echo "dev_stack is not running. Starting dev_stack..."
    docker compose -f "$DEV_STACK_COMPOSE" up -d
fi

# Check supabase container using docker compose ls
if docker compose ls | grep -q "supabase.*running"; then
    echo "supabase is running."
else
    echo "supabase is not running. Starting supabase..."
    docker compose -f "$SUPABASE_COMPOSE" up -d
fi

echo "=== Startup checks complete. ===" 