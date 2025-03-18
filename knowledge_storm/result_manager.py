"""
Result Manager module for MyValueStorm project.
This module provides a unified interface for storing and retrieving results,
with support for both local storage and S3 storage.
"""

import os
import json
import logging
from pathlib import Path
from typing import Union, List, Dict, Optional, Any

from .s3_storage import S3Storage

class ResultManager:
    """
    Class for managing STORM results with support for both local and S3 storage.
    """
    
    def __init__(self, 
                 base_dir: str = "./results", 
                 use_s3: bool = False, 
                 s3_bucket: Optional[str] = None,
                 s3_region: Optional[str] = None):
        """
        Initialize the ResultManager.
        
        Args:
            base_dir (str): Base directory for local storage
            use_s3 (bool): Whether to use S3 storage
            s3_bucket (str, optional): S3 bucket name
            s3_region (str, optional): AWS region for S3
        """
        self.base_dir = base_dir
        self.use_s3 = use_s3
        
        # Create local directory if it doesn't exist
        os.makedirs(base_dir, exist_ok=True)
        
        # Initialize S3 storage if enabled
        self.s3_storage = None
        if use_s3:
            self.s3_storage = S3Storage(bucket_name=s3_bucket, region=s3_region)
            logging.info(f"S3 storage initialized with bucket: {self.s3_storage.bucket_name}")
    
    def get_topic_dir(self, topic: str) -> str:
        """
        Get the directory path for a specific topic.
        
        Args:
            topic (str): Research topic name
            
        Returns:
            str: Path to the topic directory
        """
        # Sanitize topic name for file system
        safe_topic = topic.replace("/", "_").replace("\\", "_")
        return os.path.join(self.base_dir, safe_topic)
    
    def list_topics(self) -> List[str]:
        """
        List all available research topics.
        
        Returns:
            List[str]: List of topic names
        """
        topics = []
        
        # Check local storage
        if os.path.exists(self.base_dir):
            topics = [d for d in os.listdir(self.base_dir) 
                     if os.path.isdir(os.path.join(self.base_dir, d))]
        
        # Check S3 storage if enabled
        if self.use_s3:
            s3_topics = self.s3_storage.list_directories("")
            topics.extend([t for t in s3_topics if t not in topics])
        
        return topics
        
    def save_metadata(self, topic: str, metadata: Dict[str, Any]) -> None:
        """
        Save metadata for a research topic.
        
        Args:
            topic (str): Research topic name
            metadata (Dict[str, Any]): Metadata to save
        """
        topic_dir = self.get_topic_dir(topic)
        os.makedirs(topic_dir, exist_ok=True)
        
        metadata_path = os.path.join(topic_dir, "metadata.json")
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        if self.use_s3:
            self.s3_storage.upload_file(metadata_path, f"{topic}/metadata.json")
    
    def get_metadata(self, topic: str) -> Dict[str, Any]:
        """
        Get metadata for a research topic.
        
        Args:
            topic (str): Research topic name
            
        Returns:
            Dict[str, Any]: Metadata for the topic
        """
        topic_dir = self.get_topic_dir(topic)
        metadata_path = os.path.join(topic_dir, "metadata.json")
        
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                return json.load(f)
        elif self.use_s3:
            try:
                return json.loads(self.s3_storage.download_file(f"{topic}/metadata.json"))
            except:
                return {}
        else:
            return {}
    
    def get_article(self, topic: str) -> Dict[str, Any]:
        """
        Get article for a research topic.
        
        Args:
            topic (str): Research topic name
            
        Returns:
            Dict[str, Any]: Article data
        """
        topic_dir = self.get_topic_dir(topic)
        article_path = os.path.join(topic_dir, "article.json")
        
        if os.path.exists(article_path):
            with open(article_path, 'r') as f:
                return json.load(f)
        elif self.use_s3:
            try:
                return json.loads(self.s3_storage.download_file(f"{topic}/article.json"))
            except:
                return {}
        else:
            return {}
    
    def get_outline(self, topic: str) -> Dict[str, Any]:
        """
        Get outline for a research topic.
        
        Args:
            topic (str): Research topic name
            
        Returns:
            Dict[str, Any]: Outline data
        """
        topic_dir = self.get_topic_dir(topic)
        outline_path = os.path.join(topic_dir, "outline.json")
        
        if os.path.exists(outline_path):
            with open(outline_path, 'r') as f:
                return json.load(f)
        elif self.use_s3:
            try:
                return json.loads(self.s3_storage.download_file(f"{topic}/outline.json"))
            except:
                return {}
        else:
            return {}
            
    def save_result(self, topic: str, result_type: str, data: Union[Dict, List, str]) -> bool:
        """
        Save a result file for a topic.
        
        Args:
            topic (str): Research topic
            result_type (str): Type of result (e.g., 'outline', 'article')
            data (Union[Dict, List, str]): Data to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            topic_dir = self.get_topic_dir(topic)
            os.makedirs(topic_dir, exist_ok=True)
            
            # Determine file path and format
            file_path = os.path.join(topic_dir, f"{result_type}")
            if isinstance(data, (dict, list)):
                file_path += ".json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                file_path += ".txt"
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(str(data))
            
            # Upload to S3 if enabled
            if self.use_s3 and self.s3_storage:
                s3_key = f"{topic.lower().replace(' ', '_').replace('/', '_')}/{result_type}"
                s3_key += ".json" if isinstance(data, (dict, list)) else ".txt"
                self.s3_storage.upload_file(file_path, s3_key)
            
            return True
        
        except Exception as e:
            logging.error(f"Error saving result {result_type} for topic {topic}: {str(e)}")
            return False
    
    def get_result(self, topic: str, result_type: str, as_json: bool = True) -> Union[Dict, List, str, None]:
        """
        Get a result file for a topic.
        
        Args:
            topic (str): Research topic
            result_type (str): Type of result (e.g., 'outline', 'article')
            as_json (bool): Whether to parse as JSON
            
        Returns:
            Union[Dict, List, str, None]: Result data or None if not found
        """
        try:
            topic_dir = self.get_topic_dir(topic)
            
            # Try JSON file first
            json_path = os.path.join(topic_dir, f"{result_type}.json")
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    return json.load(f) if as_json else f.read()
            
            # Try text file
            txt_path = os.path.join(topic_dir, f"{result_type}.txt")
            if os.path.exists(txt_path):
                with open(txt_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if as_json:
                        try:
                            return json.loads(content)
                        except:
                            return content
                    return content
            
            # Try S3 if enabled
            if self.use_s3 and self.s3_storage:
                s3_prefix = topic.lower().replace(" ", "_").replace("/", "_")
                try:
                    # Try JSON first
                    content = self.s3_storage.download_file(f"{s3_prefix}/{result_type}.json")
                    return json.loads(content) if as_json else content
                except:
                    try:
                        # Try text file
                        content = self.s3_storage.download_file(f"{s3_prefix}/{result_type}.txt")
                        if as_json:
                            try:
                                return json.loads(content)
                            except:
                                return content
                        return content
                    except:
                        return None
            
            return None
        
        except Exception as e:
            logging.error(f"Error getting result {result_type} for topic {topic}: {str(e)}")
            return None
    
    def delete_topic_results(self, topic: str, delete_local: bool = True, delete_s3: bool = True) -> bool:
        """
        Delete all results for a topic.
        
        Args:
            topic (str): Research topic
            delete_local (bool): Whether to delete local files
            delete_s3 (bool): Whether to delete S3 files
            
        Returns:
            bool: True if successful, False otherwise
        """
        success = True
        
        # Delete local files
        if delete_local:
            topic_dir = self.get_topic_dir(topic)
            if os.path.exists(topic_dir):
                try:
                    import shutil
                    shutil.rmtree(topic_dir)
                except Exception as e:
                    logging.error(f"Error deleting local topic directory {topic_dir}: {str(e)}")
                    success = False
        
        # Delete S3 files
        if delete_s3 and self.use_s3 and self.s3_storage:
            s3_prefix = topic.lower().replace(" ", "_").replace("/", "_")
            if not self.s3_storage.delete_directory(s3_prefix):
                success = False
        
        return success
