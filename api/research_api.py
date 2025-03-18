"""
API endpoints for research functionality
"""

import os
import json
import uuid
import threading
from datetime import datetime
from flask import Blueprint, request, jsonify
from knowledge_storm import (
    STORMWikiRunnerArguments,
    STORMWikiRunner,
    STORMWikiLMConfigs,
)
from knowledge_storm.lm import LitellmModel
from knowledge_storm.rm import TavilySearchRM
from knowledge_storm.result_manager import ResultManager

# Create Blueprint
research_api = Blueprint('research_api', __name__)

# Global variables to track research tasks
research_tasks = {}
result_manager = ResultManager(base_dir="./results/api")

@research_api.route('/topics', methods=['GET'])
def get_topics():
    """Get list of previously researched topics"""
    try:
        # Get list of directories in results folder
        topics = result_manager.list_topics()
        return jsonify(topics)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@research_api.route('/start', methods=['POST'])
def start_research():
    """Start a new research task"""
    try:
        data = request.json
        topic = data.get('topic')
        depth = data.get('depth', 2)
        
        if not topic:
            return jsonify({"error": "Topic is required"}), 400
        
        # Create a unique ID for this research task
        research_id = str(uuid.uuid4())
        
        # Create research task object
        research_task = {
            "id": research_id,
            "topic": topic,
            "depth": depth,
            "status": "running",
            "progress": 0,
            "startTime": datetime.now().isoformat(),
            "completedTime": None
        }
        
        # Store the task
        research_tasks[research_id] = research_task
        
        # Start research in a background thread
        thread = threading.Thread(
            target=run_research,
            args=(research_id, topic, depth)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify(research_task)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@research_api.route('/progress/<research_id>', methods=['GET'])
def get_progress(research_id):
    """Get progress of a research task"""
    try:
        if research_id not in research_tasks:
            return jsonify({"error": "Research task not found"}), 404
        
        return jsonify(research_tasks[research_id])
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@research_api.route('/results', methods=['GET'])
def get_results():
    """Get list of completed research results"""
    try:
        # Get list of completed research tasks
        completed_tasks = [task for task in research_tasks.values() 
                          if task["status"] == "completed"]
        
        # If no completed tasks in memory, try to load from result_manager
        if not completed_tasks:
            topics = result_manager.list_topics()
            for topic in topics:
                try:
                    # Try to load metadata for this topic
                    metadata = result_manager.get_metadata(topic)
                    if metadata:
                        completed_tasks.append({
                            "id": metadata.get("id", str(uuid.uuid4())),
                            "topic": topic,
                            "depth": metadata.get("depth", 2),
                            "completedTime": metadata.get("completedTime", datetime.now().isoformat()),
                            "summary": metadata.get("summary", "Research on " + topic)
                        })
                except:
                    # Skip if metadata can't be loaded
                    pass
        
        return jsonify(completed_tasks)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@research_api.route('/results/<result_id>', methods=['GET'])
def get_result(result_id):
    """Get detailed result for a specific research task"""
    try:
        # First check in memory
        if result_id in research_tasks and research_tasks[result_id]["status"] == "completed":
            task = research_tasks[result_id]
            topic = task["topic"]
            
            # Try to load full result from result_manager
            try:
                article = result_manager.get_article(topic)
                outline = result_manager.get_outline(topic)
                
                # Combine data
                result = {
                    "id": result_id,
                    "topic": topic,
                    "depth": task["depth"],
                    "completedTime": task["completedTime"],
                    "summary": article.get("summary", ""),
                    "sections": [],
                    "references": []
                }
                
                # Add sections from article
                if "sections" in article:
                    result["sections"] = article["sections"]
                
                # Add references
                if "references" in article:
                    result["references"] = article["references"]
                
                return jsonify(result)
            
            except Exception as e:
                # If loading from result_manager fails, return basic info
                return jsonify({
                    "id": result_id,
                    "topic": topic,
                    "depth": task["depth"],
                    "completedTime": task["completedTime"],
                    "summary": "Research completed but full results not available",
                    "sections": [],
                    "references": []
                })
        
        # If not in memory, try to find by topic in result_manager
        topics = result_manager.list_topics()
        for topic in topics:
            try:
                metadata = result_manager.get_metadata(topic)
                if metadata and metadata.get("id") == result_id:
                    article = result_manager.get_article(topic)
                    outline = result_manager.get_outline(topic)
                    
                    # Combine data
                    result = {
                        "id": result_id,
                        "topic": topic,
                        "depth": metadata.get("depth", 2),
                        "completedTime": metadata.get("completedTime", datetime.now().isoformat()),
                        "summary": article.get("summary", ""),
                        "sections": [],
                        "references": []
                    }
                    
                    # Add sections from article
                    if "sections" in article:
                        result["sections"] = article["sections"]
                    
                    # Add references
                    if "references" in article:
                        result["references"] = article["references"]
                    
                    return jsonify(result)
            except:
                # Skip if loading fails
                pass
        
        return jsonify({"error": "Research result not found"}), 404
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def run_research(research_id, topic, depth):
    """Run STORM research in background thread"""
    try:
        # Update task status
        research_tasks[research_id]["status"] = "running"
        research_tasks[research_id]["progress"] = 5
        
        # Configure STORM
        lm_configs = STORMWikiLMConfigs()
        
        # Use environment variables or defaults for API keys
        openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID", "")
        aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
        
        # Configure LLM based on depth
        model_name = "gpt-4-turbo" if depth >= 3 else "gpt-3.5-turbo"
        
        # Initialize LLM
        lm_configs.init_openai_model(
            openai_api_key=openai_api_key,
            azure_api_key="",
            openai_type="openai",
            temperature=0.7,
            top_p=0.9
        )
        
        # Update progress
        research_tasks[research_id]["progress"] = 10
        
        # Configure retriever
        tavily_api_key = os.environ.get("TAVILY_API_KEY", "")
        retriever = TavilySearchRM(tavily_api_key)
        
        # Configure output directory
        output_dir = f"./results/api/{topic}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Update progress
        research_tasks[research_id]["progress"] = 15
        
        # Configure STORM arguments
        args = STORMWikiRunnerArguments(
            topic=topic,
            output_dir=output_dir,
            lm_configs=lm_configs,
            retriever=retriever,
            do_research=True,
            do_generate_outline=True,
            do_generate_article=True,
            do_polish_article=True
        )
        
        # Create progress callback
        class ProgressCallback:
            def __init__(self, research_id):
                self.research_id = research_id
                self.stages = {
                    "research": (20, 40),
                    "outline": (40, 60),
                    "article": (60, 80),
                    "polish": (80, 95)
                }
                self.current_stage = None
            
            def on_stage_start(self, stage):
                self.current_stage = stage
                if stage in self.stages:
                    start_progress = self.stages[stage][0]
                    research_tasks[self.research_id]["progress"] = start_progress
            
            def on_stage_end(self, stage):
                if stage in self.stages:
                    end_progress = self.stages[stage][1]
                    research_tasks[self.research_id]["progress"] = end_progress
        
        # Create callback
        callback = ProgressCallback(research_id)
        
        # Run STORM
        runner = STORMWikiRunner(args)
        
        # Update progress for each stage
        research_tasks[research_id]["progress"] = 20
        
        # Research stage
        callback.on_stage_start("research")
        runner.run_research()
        callback.on_stage_end("research")
        
        # Outline stage
        callback.on_stage_start("outline")
        runner.run_outline_generation()
        callback.on_stage_end("outline")
        
        # Article stage
        callback.on_stage_start("article")
        runner.run_article_generation()
        callback.on_stage_end("article")
        
        # Polish stage
        callback.on_stage_start("polish")
        runner.run_article_polishing()
        callback.on_stage_end("polish")
        
        # Save metadata
        metadata = {
            "id": research_id,
            "topic": topic,
            "depth": depth,
            "completedTime": datetime.now().isoformat(),
            "summary": "Research completed successfully"
        }
        
        # Save metadata to result_manager
        result_manager.save_metadata(topic, metadata)
        
        # Update task status
        research_tasks[research_id]["status"] = "completed"
        research_tasks[research_id]["progress"] = 100
        research_tasks[research_id]["completedTime"] = datetime.now().isoformat()
        
    except Exception as e:
        # Update task status on error
        if research_id in research_tasks:
            research_tasks[research_id]["status"] = "failed"
            research_tasks[research_id]["error"] = str(e)
