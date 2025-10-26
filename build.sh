#!/usr/bin/env bash
set -o errexit      # stop on any error
set -o pipefail     # catch errors in piped commands
set -o xtrace       # optional: show each command as it runs

echo "🚀 Starting project setup..."

# ---------- BACKEND SETUP ----------
echo "Installing Python dependencies..."
pip install -r requirements.txt
echo "✅ Backend dependencies installed!"

# ---------- FRONTEND CHECK ----------
if [ -d "frontend/build" ]; then
    echo "🟢 Frontend build folder already exists. Skipping rebuild."
else
    echo "⚠️ No frontend build folder found!"
    echo "You can manually build it by running:"
    echo "cd frontend && npm install && npm run build"
fi

echo "🎉 Setup finished! Your project is ready."

