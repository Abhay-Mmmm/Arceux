#!/bin/bash

# Arxis SOC Backend - Startup Script

echo "🛡️  Starting Arxis SOC Backend..."
echo ""

# Check if virtual environment is activated
if [[ -z "${VIRTUAL_ENV}" ]] && [[ -z "${CONDA_DEFAULT_ENV}" ]]; then
    echo "⚠️  Warning: No virtual environment detected"
    echo "   Recommended: conda activate lokam"
    echo ""
fi

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    echo "   Copy .env.example to .env and add your OPENAI_API_KEY"
    echo ""
fi

# Start the API server
echo "Starting FastAPI server on http://localhost:8000"
echo ""
python api.py
