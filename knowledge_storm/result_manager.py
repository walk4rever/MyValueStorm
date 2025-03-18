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
            topic (str): Research topic
            
        Returns:
            str: Path to the topic directory
        """
        # Format topic for directory name
        topic_dir_name = topic.lower().replace(" ", "_").replace("/", "_")
        return os.path.join(self.base_dir, topic_dir_name)
    
    def save_file(self, topic: str, filename: str, content: Union[str, bytes, dict]) -> str:
        """
        Save a file for a specific topic.
        
        Args:
            topic (str): Research topic
            filename (str): Name of the file
            content (Union[str, bytes, dict]): Content to save
            
        Returns:
            str: Path to the saved file
        """
        # Get the topic directory
        topic_dir = self.get_topic_dir(topic)
        
        # Create the directory if it doesn't exist
        os.makedirs(topic_dir, exist_ok=True)
        
        # Full path to the file
        file_path = os.path.join(topic_dir, filename)
        
        # Save the file locally
        if isinstance(content, dict):
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
        elif isinstance(content, bytes):
            with open(file_path, 'wb') as f:
                f.write(content)
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # Upload to S3 if enabled
        if self.use_s3 and self.s3_storage:
            s3_key = f"{os.path.basename(topic_dir)}/{filename}"
            self.s3_storage.upload_file(file_path, s3_key)
        
        return file_path
    
    def load_file(self, topic: str, filename: str, as_json: bool = False) -> Union[str, bytes, dict, None]:
        """
        Load a file for a specific topic.
        
        Args:
            topic (str): Research topic
            filename (str): Name of the file
            as_json (bool): Whether to parse the file as JSON
            
        Returns:
            Union[str, bytes, dict, None]: File content or None if not found
        """
        # Get the topic directory
        topic_dir = self.get_topic_dir(topic)
        
        # Full path to the file
        file_path = os.path.join(topic_dir, filename)
        
        # If file doesn't exist locally but S3 is enabled, try to download it
        if not os.path.exists(file_path) and self.use_s3 and self.s3_storage:
            s3_key = f"{os.path.basename(topic_dir)}/{filename}"
            if not self.s3_storage.download_file(s3_key, file_path):
                logging.warning(f"Could not download file {s3_key} from S3")
                return None
        
        # Return None if file doesn't exist
        if not os.path.exists(file_path):
            logging.warning(f"File {file_path} does not exist locally")
            return None
        
        # Load the file
        try:
            if as_json:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            logging.error(f"Error loading file {file_path}: {str(e)}")
            return None
    
    def save_results(self, topic: str, results: Dict[str, Any]) -> bool:
        """
        Save multiple result files for a topic.
        
        Args:
            topic (str): Research topic
            results (Dict[str, Any]): Dictionary of filename -> content
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            for filename, content in results.items():
                self.save_file(topic, filename, content)
            return True
        except Exception as e:
            logging.error(f"Error saving results for topic {topic}: {str(e)}")
            return False
    
    def upload_topic_results(self, topic: str) -> bool:
        """
        Upload all results for a topic to S3.
        
        Args:
            topic (str): Research topic
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.use_s3 or not self.s3_storage:
            logging.warning("S3 storage is not enabled")
            return False
        
        topic_dir = self.get_topic_dir(topic)
        if not os.path.exists(topic_dir):
            logging.error(f"Topic directory {topic_dir} does not exist")
            return False
        
        try:
            s3_prefix = os.path.basename(os.path.normpath(topic_dir))
            logging.info(f"Uploading directory {topic_dir} to S3 with prefix {s3_prefix}")
            return self.s3_storage.upload_directory(topic_dir, s3_prefix)
        except Exception as e:
            logging.error(f"Error uploading topic results: {str(e)}")
            raise e
    
    def download_topic_results(self, topic: str) -> bool:
        """
        Download all results for a topic from S3.
        
        Args:
            topic (str): Research topic
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.use_s3 or not self.s3_storage:
            logging.warning("S3 storage is not enabled")
            return False
        
        topic_dir = self.get_topic_dir(topic)
        os.makedirs(topic_dir, exist_ok=True)
        
        s3_prefix = os.path.basename(os.path.normpath(topic_dir))
        return self.s3_storage.download_directory(s3_prefix, topic_dir)
    
    def list_topics(self) -> List[str]:
        """
        List all available topics.
        
        Returns:
            List[str]: List of topic names
        """
        topics = []
        
        # List local topics
        if os.path.exists(self.base_dir):
            for item in os.listdir(self.base_dir):
                if os.path.isdir(os.path.join(self.base_dir, item)):
                    topics.append(item)
        
        # List S3 topics if enabled
        if self.use_s3 and self.s3_storage:
            s3_keys = self.s3_storage.list_files()
            for key in s3_keys:
                parts = key.split('/')
                if len(parts) > 1:
                    topic = parts[0]
                    if topic not in topics:
                        topics.append(topic)
        
        return topics
    
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
