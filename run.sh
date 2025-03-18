
#!/bin/bash

# Make script exit on any error
set -e

source .env.aws

# Test Tavily API directly
echo "Testing Tavily API directly..."
python ./test_tavily.py

# Activate conda environment
echo "Activating conda environment..."
conda activate storm

# Install knowledge_storm locally
# pip install -e .

# Run the script
echo "Running STORM with Bedrock..."
python examples/storm_examples/run_storm_wiki_bedrock.py \
    --output-dir ./results/bedrock \
    --do-research \
    --do-generate-outline \
    --do-generate-article \
    --do-polish-article
