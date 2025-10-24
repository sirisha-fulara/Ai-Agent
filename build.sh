#!/usr/bin/env bash
set -o errexit  # stop if any command fails

# ---------- FRONTEND BUILD ----------
cd frontend
npm install
npm run build

# ---------- BACKEND SETUP ----------
cd ..
pip install -r requirements.txt
