#!/bin/bash

# Script to set up and run the Vue.js frontend for ValueStorm

# Exit on error
set -e

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Node.js is not installed. Please install Node.js and npm first."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "npm is not installed. Please install npm first."
    exit 1
fi

# Navigate to the Vue.js project directory
cd "$(dirname "$0")/frontend/vue-ui"

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "Installing Vue.js dependencies..."
    npm install
fi

# Build the Vue.js application for production
echo "Building Vue.js application..."
npm run build

# Navigate back to the project root
cd "$(dirname "$0")"

# Run the Flask application that serves the Vue.js frontend
echo "Starting the Flask server for Vue.js frontend..."
python app_with_vue.py
