import streamlit as st
import os
import json
import time
import tempfile
from pathlib import Path
import litellm
import boto3
import logging
from botocore.exceptions import ClientError

from knowledge_storm import (
    STORMWikiRunnerArguments,
    STORMWikiRunner,
    STORMWikiLMConfigs,
)
from knowledge_storm.lm import LitellmModel
from knowledge_storm.rm import TavilySearchRM
from knowledge_storm.s3_storage import S3Storage

# Configure logging
logging.basicConfig(level=logging.INFO)

# Set page configuration
st.set_page_config(
    page_title="STORM Research Assistant",
    page_icon="🌪️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Disable the default Streamlit menu and footer
hide_menu_style = """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .stDeployButton {display:none;}
        .css-1rs6os {visibility: hidden;}
        .css-17ziqus {visibility: hidden;}
    </style>
"""
st.markdown(hide_menu_style, unsafe_allow_html=True)

# Load custom CSS
try:
    with open('static/custom.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("Custom CSS file not found. Using default styling.")

# Initialize session state
if 'selected_topic' not in st.session_state:
    st.session_state.selected_topic = None
if 'temp_dir' not in st.session_state:
    st.session_state.temp_dir = tempfile.mkdtemp()

# S3 Configuration
S3_BUCKET = os.environ.get("S3_BUCKET", "mystorm-results")
S3_REGION = os.environ.get("AWS_REGION", "us-west-2")

# Model Configuration
MODEL_PROVIDER = "bedrock"
TEMPERATURE = 0.7
TOP_P = 0.9
MAX_TOKENS = 4000
NUM_SEARCH_RESULTS = 10

# Initialize S3 client
try:
    s3_client = boto3.client('s3', region_name=S3_REGION)
    s3_storage = S3Storage(bucket_name=S3_BUCKET, region=S3_REGION)
except Exception as e:
    st.error(f"Failed to initialize S3 client: {str(e)}")
    st.stop()

@st.cache_data(ttl=3600)
def list_topics_from_s3():
    try:
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Delimiter='/'
        )
        
        topics = []
        if 'CommonPrefixes' in response:
            for prefix in response['CommonPrefixes']:
                # Extract topic name from prefix (remove trailing slash)
                topic = prefix['Prefix'].rstrip('/')
                topics.append(topic)
        
        return topics
    except Exception as e:
        st.error(f"Error listing topics from S3: {str(e)}")
        return []

@st.cache_data(ttl=3600)
def download_file_from_s3(s3_key, local_path):
    try:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        s3_client.download_file(S3_BUCKET, s3_key, local_path)
        return True
    except Exception as e:
        logging.error(f"Error downloading {s3_key}: {str(e)}")
        return False

@st.cache_data(ttl=3600)
def download_topic_files(topic):
    temp_topic_dir = os.path.join(st.session_state.temp_dir, topic)
    os.makedirs(temp_topic_dir, exist_ok=True)
    
    try:
        # List all objects with the topic prefix
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=f"{topic}/"
        )
        
        if 'Contents' in response:
            for obj in response['Contents']:
                s3_key = obj['Key']
                filename = os.path.basename(s3_key)
                local_path = os.path.join(temp_topic_dir, filename)
                download_file_from_s3(s3_key, local_path)
        
        return temp_topic_dir
    except Exception as e:
        st.error(f"Error downloading topic files: {str(e)}")
        return None

# Function to upload a file to S3
def upload_file_to_s3(local_path, s3_key):
    try:
        s3_client.upload_file(local_path, S3_BUCKET, s3_key)
        return True
    except Exception as e:
        logging.error(f"Error uploading {local_path} to {s3_key}: {str(e)}")
        return False

# Function to upload a directory to S3
def upload_directory_to_s3(local_dir, s3_prefix):
    success = True
    for root, _, files in os.walk(local_dir):
        for file in files:
            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, local_dir)
            s3_key = f"{s3_prefix}/{relative_path}"
            if not upload_file_to_s3(local_path, s3_key):
                success = False
    return success

# Sidebar
with st.sidebar:
    st.title("🌪️ STORM Research")
    
    # Get available topics
    topics = list_topics_from_s3()
    topics = [topic.replace('_', ' ').title() for topic in topics]
    
    # Topic selection
    st.subheader("Explore Research")
    if topics:
        selected_topic = st.selectbox(
            "Select a topic to view",
            [""] + topics,
            index=0
        )
        
        if selected_topic:
            st.session_state.selected_topic = selected_topic.lower().replace(' ', '_')
            
            if st.button("View Research", type="primary"):
                st.rerun()
    else:
        st.info("No research topics available yet")
    
    # New research section
    st.markdown("---")
    st.subheader("New Research")
    new_topic = st.text_input("Enter a research topic")
    
    start_research = st.button("Start Research", type="primary", key="start_research")
    
    # Display S3 status
    st.markdown("---")
    st.caption(f"Using S3 bucket: {S3_BUCKET} in {S3_REGION}")

# Main content area
if st.session_state.selected_topic:
    # Download topic files from S3
    with st.spinner(f"Loading research data..."):
        topic_dir = download_topic_files(st.session_state.selected_topic)
    
    if not topic_dir:
        st.error("Failed to download research data. Please try again.")
        st.stop()
    
    # Display the topic title
    st.title(f"📊 {st.session_state.selected_topic.replace('_', ' ').title()}")
    
    # Create tabs for better organization
    tab1, tab2 = st.tabs(["Research Article", "Sources & References"])
    
    with tab1:
        # Check for polished article first (best version)
        polished_path = os.path.join(topic_dir, "storm_gen_article_polished.txt")
        article_path = os.path.join(topic_dir, "storm_gen_article.txt")
        
        # Display the article content
        if os.path.exists(polished_path):
            with open(polished_path, 'r') as f:
                article_content = f.read()
                st.markdown(f'<div class="markdown-text-container">{article_content}</div>', unsafe_allow_html=True)
        elif os.path.exists(article_path):
            with open(article_path, 'r') as f:
                article_content = f.read()
                st.markdown(f'<div class="markdown-text-container">{article_content}</div>', unsafe_allow_html=True)
        else:
            st.warning("No article content found for this topic.")
    
    # Add a table of contents in the sidebar
    with st.sidebar:
        with st.expander("Table of Contents", expanded=True):
            storm_outline_path = os.path.join(topic_dir, "storm_gen_outline.txt")
            if os.path.exists(storm_outline_path):
                with open(storm_outline_path, 'r') as f:
                    outline_content = f.read()
                    # Format the outline as clickable links
                    lines = outline_content.split('\n')
                    toc_html = "<div class='table-of-contents'>"
                    for line in lines:
                        if line.strip():
                            # Count leading # to determine heading level
                            level = 0
                            for char in line:
                                if char == '#':
                                    level += 1
                                else:
                                    break
                            
                            if level > 0:
                                title = line.strip('# ')
                                # Create anchor from title
                                anchor = title.lower().replace(' ', '-')
                                indent = (level - 1) * 20
                                toc_html += f"<div style='margin-left: {indent}px;'><a href='#{anchor}'>{title}</a></div>"
                    
                    toc_html += "</div>"
                    st.markdown(toc_html, unsafe_allow_html=True)
    
    # Display outline in the sidebar
    with st.sidebar:
        with st.expander("Research Outline", expanded=False):
            storm_outline_path = os.path.join(topic_dir, "storm_gen_outline.txt")
            if os.path.exists(storm_outline_path):
                with open(storm_outline_path, 'r') as f:
                    st.code(f.read(), language=None)
    
    # Check for polished article first (best version)
    polished_path = os.path.join(topic_dir, "storm_gen_article_polished.txt")
    article_path = os.path.join(topic_dir, "storm_gen_article.txt")
    
    # Display the article content
    if os.path.exists(polished_path):
        with open(polished_path, 'r') as f:
            article_content = f.read()
            st.markdown(f'<div class="markdown-text-container">{article_content}</div>', unsafe_allow_html=True)
    elif os.path.exists(article_path):
        with open(article_path, 'r') as f:
            article_content = f.read()
            st.markdown(f'<div class="markdown-text-container">{article_content}</div>', unsafe_allow_html=True)
    else:
        st.warning("No article content found for this topic.")
    
    # Display sources at the bottom
    sources_path = os.path.join(topic_dir, "url_to_info.json")
    if os.path.exists(sources_path):
        with tab2:
            try:
                with open(sources_path, 'r') as f:
                    sources = json.load(f)
                    if "url_to_info" in sources:
                        st.markdown('<div class="source-grid">', unsafe_allow_html=True)
                        cols = st.columns(3)
                        i = 0
                        for url, info in sources["url_to_info"].items():
                            with cols[i % 3]:
                                st.markdown(f"""
                                <div class="source-card">
                                    <strong><a href="{url}" target="_blank">{info.get('title', 'Source')}</a></strong>
                                    <p><em>{info.get('description', '')[:100]}...</em></p>
                                </div>
                                """, unsafe_allow_html=True)
                            i += 1
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.info("No source information found.")
            except Exception as e:
                st.error(f"Error loading sources: {str(e)}")

elif start_research and new_topic:
    # Start new research
    st.title(f"🔍 Researching: {new_topic}")
    
    # Create progress tracking with animation
    progress_placeholder = st.empty()
    with progress_placeholder.container():
        progress_bar = st.progress(0)
        status = st.empty()
    
    # Add a spinner animation
    spinner_html = """
    <style>
    .loading-spinner {
        display: flex;
        justify-content: center;
        margin: 20px 0;
    }
    .loading-spinner::after {
        content: "";
        width: 50px;
        height: 50px;
        border: 10px solid #f3f3f3;
        border-top: 10px solid #3498db;
        border-radius: 50%;
        animation: spinner 1s linear infinite;
    }
    @keyframes spinner {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    </style>
    <div class="loading-spinner"></div>
    """
    spinner = st.empty()
    spinner.markdown(spinner_html, unsafe_allow_html=True)
    
    try:
        # Check for Tavily API key
        tavily_api_key = os.environ.get("TAVILY_API_KEY")
        if not tavily_api_key:
            st.error("TAVILY_API_KEY environment variable not found. Please set it before running.")
            st.stop()
        
        # Create a temporary directory for this research
        topic_dir_name = new_topic.lower().replace(" ", "_").replace("/", "_")
        temp_topic_dir = os.path.join(st.session_state.temp_dir, topic_dir_name)
        os.makedirs(temp_topic_dir, exist_ok=True)
        
        # Configure STORM
        status.info("Setting up research environment...")
        progress_bar.progress(10)
        
        lm_configs = STORMWikiLMConfigs()
        
        # Model configuration
        model_kwargs = {
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
        }
        
        # Initialize model based on provider
        if MODEL_PROVIDER == "bedrock":
            bedrock_model = "anthropic.claude-3-sonnet-20240229-v1:0"
            model_name = "bedrock/" + bedrock_model
            
            # Test model access
            try:
                status.info("Testing model access...")
                litellm.completion(
                    model=model_name,
                    messages=[{"role": "user", "content": "Hello, are you working?"}],
                    max_tokens=10
                )
            except Exception as e:
                status.error(f"Error accessing model: {str(e)}")
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
        status.info("Setting up search capabilities...")
        progress_bar.progress(20)
        
        rm = TavilySearchRM(
            tavily_search_api_key=tavily_api_key,
            k=NUM_SEARCH_RESULTS,
            include_raw_content=True
        )
        
        # Set up STORM arguments
        storm_args = STORMWikiRunnerArguments(
            output_dir=st.session_state.temp_dir,
            search_top_k=NUM_SEARCH_RESULTS
        )
        
        # Initialize STORM runner
        runner = STORMWikiRunner(
            args=storm_args,
            lm_configs=lm_configs,
            rm=rm
        )
        
        # Execute STORM with progress updates
        status.info("Researching topic...")
        progress_bar.progress(30)
        
        # Research phase
        status.info("Gathering information...")
        runner.run(
            topic=new_topic,
            do_research=True,
            do_generate_outline=False,
            do_generate_article=False,
            do_polish_article=False
        )
        progress_bar.progress(50)
        
        # Outline phase
        status.info("Creating research outline...")
        runner.run(
            topic=new_topic,
            do_research=False,
            do_generate_outline=True,
            do_generate_article=False,
            do_polish_article=False
        )
        progress_bar.progress(60)
        
        # Article generation phase
        status.info("Writing initial article draft...")
        runner.run(
            topic=new_topic,
            do_research=False,
            do_generate_outline=False,
            do_generate_article=True,
            do_polish_article=False
        )
        progress_bar.progress(80)
        
        # Polish phase
        status.info("Polishing and finalizing article...")
        runner.run(
            topic=new_topic,
            do_research=False,
            do_generate_outline=False,
            do_generate_article=False,
            do_polish_article=True
        )
        progress_bar.progress(90)
        
        # Upload results to S3
        status.info("Saving research to cloud storage...")
        try:
            upload_success = upload_directory_to_s3(temp_topic_dir, topic_dir_name)
            if upload_success:
                status.success("Research saved to cloud storage successfully!")
            else:
                status.warning("Some files could not be uploaded to cloud storage.")
        except Exception as e:
            status.warning(f"Could not upload to cloud storage: {str(e)}")
            st.exception(e)
        
        progress_bar.progress(100)
        status.success("Research completed successfully!")
        
        # Set the selected topic to view results
        st.session_state.selected_topic = topic_dir_name
        time.sleep(2)  # Give user time to see the success message
        st.rerun()
        
    except Exception as e:
        status.error(f"Error during research process: {str(e)}")
        st.exception(e)
else:
    # Welcome screen with a more modern design
    st.title("🌪️ STORM Research Assistant")
    
    # Create a two-column layout for the welcome screen
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        <div class="welcome-container">
            <h2>Welcome to STORM Research</h2>
            
            <p>STORM (STructured Outline-based Research Method) helps you create comprehensive research articles
            by gathering information, generating outlines, and writing well-structured content.</p>
            
            <h3>Getting Started</h3>
            
            <ol>
                <li><strong>Explore existing research</strong> by selecting a topic from the sidebar</li>
                <li><strong>Start new research</strong> by entering a topic and clicking "Start Research"</li>
            </ol>
            
            <h3>How It Works</h3>
            
            <p>STORM uses advanced AI to:</p>
            <ul>
                <li>Research your topic from reliable sources</li>
                <li>Create a structured outline</li>
                <li>Generate a comprehensive article</li>
                <li>Polish and refine the content</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Add a visual element
        st.markdown("""
        <div style="background-color: #f0f4f8; border-radius: 12px; padding: 20px; text-align: center; height: 100%;">
            <div style="font-size: 80px; margin-bottom: 20px;">🌪️</div>
            <h3 style="margin-top: 0;">Powerful AI Research</h3>
            <p>Transform complex topics into clear, structured articles</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Show a sample of available topics
    if topics:
        st.subheader("Available Research Topics")
        
        # Create a grid layout for topics with cards
        st.markdown("""
        <style>
        .topic-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .topic-card {
            background-color: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            cursor: pointer;
            border: 1px solid #e2e8f0;
        }
        .topic-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 15px rgba(0,0,0,0.1);
        }
        .topic-icon {
            font-size: 24px;
            margin-bottom: 10px;
        }
        </style>
        <div class="topic-grid">
        """, unsafe_allow_html=True)
        
        for i, topic in enumerate(topics[:9]):  # Show up to 9 topics
            clean_topic = topic.replace("'", "\\'").replace('"', '\\"')
            st.markdown(f"""
            <div class="topic-card" onclick="window.location.href='#'" id="topic-{i}">
                <div class="topic-icon">📄</div>
                <h3>{clean_topic}</h3>
                <p>Click to view research</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Add JavaScript to handle the click
            st.markdown(f"""
            <script>
            document.getElementById('topic-{i}').addEventListener('click', function() {{
                const selectBox = window.parent.document.querySelector('div[data-testid="stSelectbox"] select');
                if (selectBox) {{
                    selectBox.value = "{clean_topic}";
                    selectBox.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    
                    // Find and click the "View Research" button
                    const buttons = window.parent.document.querySelectorAll('button');
                    for (let button of buttons) {{
                        if (button.innerText.includes('View Research')) {{
                            button.click();
                            break;
                        }}
                    }}
                }}
            }});
            </script>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
