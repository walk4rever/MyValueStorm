#!/bin/bash

# Script to run the Vue.js frontend with Flask backend

# Exit on error
set -e

echo "Starting ValueStorm with Vue.js frontend..."

# Install required Python packages if not already installed
pip install flask

# Check if Vue.js frontend is built
if [ ! -d "frontend/vue-ui/dist" ]; then
  echo "Building Vue.js frontend..."
  cd frontend/vue-ui
  npm install
  npm run build
  cd ../..
fi

# Run the Flask application that serves the Vue.js frontend
python app_with_vue.py
