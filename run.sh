#!/bin/bash

# Make script exit on any error
set -e

# Load environment variables
source .env.aws

# Set Tavily API key if it exists in .env.aws
if [ -n "$TAVILY_API_KEY" ]; then
  export TAVILY_API_KEY=$TAVILY_API_KEY
else
  echo "Warning: TAVILY_API_KEY not found in .env.aws"
fi

# Ensure AWS credentials are available
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
  echo "Error: AWS credentials not found. Please ensure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set in .env.aws"
  exit 1
fi

# Set AWS region to us-west-2 if not specified
export AWS_REGION=${AWS_REGION:-us-west-2}
echo "Using AWS region: $AWS_REGION"
echo "Using S3 bucket: ${S3_BUCKET:-mystorm-results}"

# Run the S3-only Streamlit app
echo "Starting STORM Streamlit UI with S3-only storage..."
S3_BUCKET=${S3_BUCKET:-mystorm-results} streamlit run app_simplified.py
