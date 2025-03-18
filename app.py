import streamlit as st
import os
import json
import time
from pathlib import Path
import subprocess
import litellm
import sys

from knowledge_storm import (
    STORMWikiRunnerArguments,
    STORMWikiRunner,
    STORMWikiLMConfigs,
)
from knowledge_storm.lm import LitellmModel
from knowledge_storm.rm import TavilySearchRM
from knowledge_storm.result_manager import ResultManager

# Set page configuration
st.set_page_config(
    page_title="STORM Research Assistant",
    page_icon="🌪️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar for configuration
st.sidebar.title("STORM Configuration")

# Topic input
topic = st.sidebar.text_input("Research Topic", "")

# Output directory
output_dir = st.sidebar.text_input("Output Directory", "./results/streamlit")

# Storage options
default_storage_index = 1 if os.environ.get("S3_ENABLED", "").lower() == "true" else 0
storage_option = st.sidebar.radio(
    "Storage Option",
    ["Local Storage", "AWS S3"],
    index=default_storage_index
)

# S3 bucket name (only shown if S3 is selected)
s3_bucket = None
s3_region = None
if storage_option == "AWS S3":
    s3_bucket = st.sidebar.text_input("S3 Bucket Name", os.environ.get("S3_BUCKET", "mystorm-results"))
    s3_region = st.sidebar.text_input("AWS Region", os.environ.get("AWS_REGION", "us-east-1"))

# Model selection
model_provider = st.sidebar.selectbox(
    "Model Provider",
    ["bedrock", "openai", "anthropic"],
    index=0
)

# Process steps selection
st.sidebar.subheader("Process Steps")
do_research = st.sidebar.checkbox("Research", value=True)
do_generate_outline = st.sidebar.checkbox("Generate Outline", value=True)
do_generate_article = st.sidebar.checkbox("Generate Article", value=True)
do_polish_article = st.sidebar.checkbox("Polish Article", value=True)

# Advanced options (collapsible)
with st.sidebar.expander("Advanced Options"):
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7)
    top_p = st.slider("Top P", 0.0, 1.0, 0.9)
    max_tokens = st.number_input("Max Tokens", 1000, 10000, 4000)
    num_search_results = st.number_input("Number of Search Results", 3, 20, 10)
    
# Main content
st.title("🌪️ STORM Research Assistant")
st.write("""
STORM (STructured Outline-based Research Method) helps you create comprehensive research articles
by gathering information, generating outlines, and writing well-structured content.
""")

# Function to display results
def display_results(output_path):
    st.subheader("Research Results")
    
    # Check for conversation log
    conv_log_path = os.path.join(output_path, "conversation_log.json")
    if os.path.exists(conv_log_path):
        with st.expander("Research Conversation"):
            try:
                # Check file size first
                file_size = os.path.getsize(conv_log_path)
                if file_size > 1000000:  # If file is larger than ~1MB
                    st.warning(f"Conversation log is very large ({file_size/1000000:.2f} MB). Showing only the first few exchanges.")
                    
                    # Read the first part of the file to extract some conversations
                    with open(conv_log_path, 'r') as f:
                        # Read first 100KB which should contain the first few exchanges
                        content = f.read(100000)
                        try:
                            # Try to find a valid JSON array start and end
                            if content.startswith('['):
                                # Find the last complete object in the partial JSON
                                last_complete = content.rfind('},')
                                if last_complete > 0:
                                    partial_content = content[:last_complete+1] + ']'
                                    try:
                                        partial_data = json.loads(partial_content)
                                        # Display the first few exchanges
                                        for i, item in enumerate(partial_data):
                                            if "dlg_turns" in item:
                                                for turn in item["dlg_turns"]:
                                                    if "user_utterance" in turn:
                                                        st.markdown(f"**User:** {turn['user_utterance']}")
                                                    if "agent_utterance" in turn:
                                                        st.markdown(f"**Assistant:** {turn['agent_utterance']}")
                                                    st.divider()
                                            elif "user" in item:
                                                st.markdown(f"**User:** {item['user']}")
                                            elif "assistant" in item:
                                                st.markdown(f"**Assistant:** {item['assistant']}")
                                    except json.JSONDecodeError:
                                        st.error("Could not parse the conversation log format.")
                        except Exception as e:
                            st.error(f"Error processing conversation: {str(e)}")
                else:
                    # For smaller files, load the entire content
                    with open(conv_log_path, 'r') as f:
                        conv_data = json.load(f)
                        
                        # Check if the data is in the expected format
                        if isinstance(conv_data, list):
                            for i, item in enumerate(conv_data):
                                # Handle different conversation formats
                                if "dlg_turns" in item:
                                    # Format with dialog turns
                                    for turn in item["dlg_turns"]:
                                        if "user_utterance" in turn:
                                            st.markdown(f"**User:** {turn['user_utterance']}")
                                        if "agent_utterance" in turn:
                                            st.markdown(f"**Assistant:** {turn['agent_utterance']}")
                                        st.divider()
                                elif "user" in item:
                                    st.markdown(f"**User:** {item['user']}")
                                    if "assistant" in item:
                                        st.markdown(f"**Assistant:** {item['assistant']}")
                                    st.divider()
                        else:
                            st.error("Conversation log is not in the expected format.")
            except Exception as e:
                st.error(f"Error loading conversation log: {str(e)}")
                st.info("The conversation log file might be too large or in an unexpected format. Try viewing it directly in a text editor.")
    
    # Check for outlines
    direct_outline_path = os.path.join(output_path, "direct_gen_outline.txt")
    storm_outline_path = os.path.join(output_path, "storm_gen_outline.txt")
    
    # Debug information
    st.write(f"Looking for files in: {output_path}")
    st.write(f"Direct outline exists: {os.path.exists(direct_outline_path)}")
    st.write(f"STORM outline exists: {os.path.exists(storm_outline_path)}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if os.path.exists(direct_outline_path):
            st.subheader("Direct Generated Outline")
            with open(direct_outline_path, 'r') as f:
                st.text_area("", f.read(), height=300)
    
    with col2:
        if os.path.exists(storm_outline_path):
            st.subheader("STORM Generated Outline")
            try:
                with open(storm_outline_path, 'r') as f:
                    outline_content = f.read()
                    st.text_area("", outline_content, height=300)
            except Exception as e:
                st.error(f"Error reading STORM outline: {str(e)}")
                st.info(f"File exists: {os.path.exists(storm_outline_path)}, Size: {os.path.getsize(storm_outline_path) if os.path.exists(storm_outline_path) else 'N/A'}")
    
    # Check for articles
    article_path = os.path.join(output_path, "storm_gen_article.txt")
    polished_path = os.path.join(output_path, "storm_gen_article_polished.txt")
    
    if os.path.exists(article_path):
        st.subheader("Generated Article")
        with open(article_path, 'r') as f:
            st.markdown(f.read())
    
    if os.path.exists(polished_path):
        st.subheader("Polished Article")
        with open(polished_path, 'r') as f:
            st.markdown(f.read())
    
    # Check for sources
    sources_path = os.path.join(output_path, "url_to_info.json")
    if os.path.exists(sources_path):
        with st.expander("Sources"):
            try:
                with open(sources_path, 'r') as f:
                    sources = json.load(f)
                    if "url_to_info" in sources:
                        for url, info in sources["url_to_info"].items():
                            st.markdown(f"**[{info.get('title', 'Source')}]({url})**")
                            st.markdown(f"_{info.get('description', '')}_")
                            if "snippets" in info and info["snippets"]:
                                st.markdown(f"Snippet: {info['snippets'][0][:200]}...")
                            st.divider()
                    else:
                        st.info("No source information found in the expected format.")
            except Exception as e:
                st.error(f"Error loading sources: {str(e)}")

# Run STORM process
if st.sidebar.button("Start STORM Process"):
    if not topic:
        st.error("Please enter a research topic")
    else:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Format topic for directory name
        topic_dir_name = topic.lower().replace(" ", "_").replace("/", "_")
        full_output_path = os.path.join(output_dir, topic_dir_name)
        os.makedirs(full_output_path, exist_ok=True)
        
        # Create a progress bar
        progress_bar = st.progress(0)
        status = st.empty()
        
        try:
            status.info(f"Starting STORM process for topic: {topic}")
            
            # Check for Tavily API key
            tavily_api_key = os.environ.get("TAVILY_API_KEY")
            if not tavily_api_key:
                status.error("TAVILY_API_KEY environment variable not found. Please set it before running.")
                st.stop()
            
            # Initialize result manager
            use_s3 = (storage_option == "AWS S3")
            result_manager = ResultManager(
                base_dir=output_dir,
                use_s3=use_s3,
                s3_bucket=s3_bucket,
                s3_region=s3_region
            )
            
            # Format topic for directory name
            topic_dir_name = topic.lower().replace(" ", "_").replace("/", "_")
            full_output_path = result_manager.get_topic_dir(topic)
            os.makedirs(full_output_path, exist_ok=True)
            
            # Configure STORM
            lm_configs = STORMWikiLMConfigs()
            
            # Model configuration based on provider
            model_kwargs = {
                "temperature": temperature,
                "top_p": top_p,
            }
            
            # Test model access first
            status.info("Testing model access...")
            
            # Initialize model variables
            conv_simulator_lm = None
            question_asker_lm = None
            outline_gen_lm = None
            article_gen_lm = None
            article_polish_lm = None
            
            if model_provider == "bedrock":
                bedrock_model = "anthropic.claude-3-sonnet-20240229-v1:0"
                model_name = "bedrock/" + bedrock_model
                
                # Test model access
                try:
                    litellm.completion(
                        model=model_name,
                        messages=[{"role": "user", "content": "Hello, are you working?"}],
                        max_tokens=10
                    )
                    status.success("Model access successful!")
                except Exception as e:
                    status.error(f"Error accessing Bedrock model: {str(e)}")
                    st.exception(e)
                    st.stop()
                
                # Set up all the required LMs
                conv_simulator_lm = LitellmModel(model=model_name, max_tokens=500, **model_kwargs)
                question_asker_lm = LitellmModel(model=model_name, max_tokens=500, **model_kwargs)
                outline_gen_lm = LitellmModel(model=model_name, max_tokens=400, **model_kwargs)
                article_gen_lm = LitellmModel(model=model_name, max_tokens=700, **model_kwargs)
                article_polish_lm = LitellmModel(model=model_name, max_tokens=4000, **model_kwargs)
                
            elif model_provider == "openai":
                model_name = "gpt-4-turbo"
                
                # Test model access
                try:
                    litellm.completion(
                        model=model_name,
                        messages=[{"role": "user", "content": "Hello, are you working?"}],
                        max_tokens=10
                    )
                    status.success("Model access successful!")
                except Exception as e:
                    status.error(f"Error accessing OpenAI model: {str(e)}")
                    st.exception(e)
                    st.stop()
                
                # Set up all the required LMs
                conv_simulator_lm = LitellmModel(model=model_name, max_tokens=500, **model_kwargs)
                question_asker_lm = LitellmModel(model=model_name, max_tokens=500, **model_kwargs)
                outline_gen_lm = LitellmModel(model=model_name, max_tokens=400, **model_kwargs)
                article_gen_lm = LitellmModel(model=model_name, max_tokens=700, **model_kwargs)
                article_polish_lm = LitellmModel(model=model_name, max_tokens=4000, **model_kwargs)
                
            elif model_provider == "anthropic":
                model_name = "claude-3-sonnet-20240229"
                
                # Test model access
                try:
                    litellm.completion(
                        model=model_name,
                        messages=[{"role": "user", "content": "Hello, are you working?"}],
                        max_tokens=10
                    )
                    status.success("Model access successful!")
                except Exception as e:
                    status.error(f"Error accessing Anthropic model: {str(e)}")
                    st.exception(e)
                    st.stop()
                
                # Set up all the required LMs
                conv_simulator_lm = LitellmModel(model=model_name, max_tokens=500, **model_kwargs)
                question_asker_lm = LitellmModel(model=model_name, max_tokens=500, **model_kwargs)
                outline_gen_lm = LitellmModel(model=model_name, max_tokens=400, **model_kwargs)
                article_gen_lm = LitellmModel(model=model_name, max_tokens=700, **model_kwargs)
                article_polish_lm = LitellmModel(model=model_name, max_tokens=4000, **model_kwargs)
            
            # Set the LMs in the config
            lm_configs.set_conv_simulator_lm(conv_simulator_lm)
            lm_configs.set_question_asker_lm(question_asker_lm)
            lm_configs.set_outline_gen_lm(outline_gen_lm)
            lm_configs.set_article_gen_lm(article_gen_lm)
            lm_configs.set_article_polish_lm(article_polish_lm)
            
            # Configure retrieval model
            status.info("Setting up retrieval model...")
            rm = TavilySearchRM(
                tavily_search_api_key=tavily_api_key,
                k=num_search_results,
                include_raw_content=True
            )
            
            # Test Tavily search
            try:
                status.info("Testing Tavily search API...")
                test_results = rm.forward("test query")
                if not test_results:
                    status.warning("Tavily search returned no results for test query, but API is working")
                else:
                    status.success("Tavily search is working!")
            except Exception as e:
                status.error(f"Error with Tavily search: {str(e)}")
                st.exception(e)
                st.stop()
            
            # Set up STORM arguments
            storm_args = STORMWikiRunnerArguments(
                output_dir=output_dir,
                search_top_k=num_search_results
            )
            
            # Initialize STORM runner
            status.info("Initializing STORM runner...")
            runner = STORMWikiRunner(
                args=storm_args,
                lm_configs=lm_configs,
                rm=rm
            )
            
            # Update progress
            progress_bar.progress(10)
            status.info("Starting research process...")
            
            # Execute STORM
            runner.run(
                topic=topic,
                do_research=do_research,
                do_generate_outline=do_generate_outline,
                do_generate_article=do_generate_article,
                do_polish_article=do_polish_article
            )
            
            # Update progress
            progress_bar.progress(100)
            
            # Upload results to S3 if enabled
            if use_s3:
                status.info("Uploading results to S3...")
                try:
                    if result_manager.upload_topic_results(topic):
                        status.success("Results uploaded to S3 successfully!")
                    else:
                        status.error("Failed to upload results to S3")
                except Exception as e:
                    status.error(f"Error uploading to S3: {str(e)}")
                    st.exception(e)
            
            status.success("STORM process completed successfully!")
            
            # Display results
            display_results(full_output_path)
            
        except Exception as e:
            status.error(f"Error during STORM process: {str(e)}")
            st.exception(e)

# Check for existing results
if st.sidebar.button("Load Previous Results"):
    if not topic:
        st.error("Please enter a topic to load its results")
    else:
        # Initialize result manager with the same settings
        use_s3 = (storage_option == "AWS S3")
        result_manager = ResultManager(
            base_dir=output_dir,
            use_s3=use_s3,
            s3_bucket=s3_bucket,
            s3_region=s3_region
        )
        
        topic_dir_name = topic.lower().replace(" ", "_").replace("/", "_")
        full_output_path = result_manager.get_topic_dir(topic)
        
        # If using S3, try to download the results first
        if use_s3:
            status = st.empty()
            status.info(f"Downloading results for topic: {topic} from S3...")
            if result_manager.download_topic_results(topic):
                status.success("Results downloaded from S3 successfully!")
            else:
                status.warning("Could not find results in S3 or download failed")
        
        if os.path.exists(full_output_path):
            display_results(full_output_path)
        else:
            st.error(f"No results found for topic: {topic}")

# Add a section to list available topics
if st.sidebar.button("List Available Topics"):
    # Initialize result manager with the same settings
    use_s3 = (storage_option == "AWS S3")
    result_manager = ResultManager(
        base_dir=output_dir,
        use_s3=use_s3,
        s3_bucket=s3_bucket,
        s3_region=s3_region
    )
    
    topics = result_manager.list_topics()
    if topics:
        st.sidebar.subheader("Available Topics:")
        for topic in topics:
            st.sidebar.markdown(f"- {topic.replace('_', ' ').title()}")
    else:
        st.sidebar.info("No topics found")

# Add a section to monitor progress
st.sidebar.markdown("---")
st.sidebar.markdown("STORM: STructured Outline-based Research Method")
st.sidebar.markdown("Built with Streamlit")

# Add S3 storage information if enabled
if storage_option == "AWS S3":
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**S3 Storage:** {s3_bucket}")
    st.sidebar.markdown(f"**Region:** {s3_region}")
