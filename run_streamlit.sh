#!/bin/bash

# Make script exit on any error
#set -e

# Load environment variables
source .env.aws

# Activate conda environment if needed
# conda activate storm

# Install knowledge_storm locally if needed
# pip install -e .

# Run the Streamlit app
echo "Starting STORM Streamlit UI..."
streamlit run app.py
