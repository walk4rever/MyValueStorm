"""
S3 Storage module for MyValueStorm project.
This module provides functionality to store and retrieve results in an AWS S3 bucket.
"""

import os
import json
import boto3
import logging
from pathlib import Path
from botocore.exceptions import ClientError

class S3Storage:
    """
    Class for handling storage and retrieval of STORM results in an AWS S3 bucket.
    """
    
    def __init__(self, bucket_name=None, region=None):
        """
        Initialize the S3Storage class.
        
        Args:
            bucket_name (str, optional): Name of the S3 bucket to use. If None, will use 'mystorm-results' by default.
            region (str, optional): AWS region to use. If None, will use the region from AWS_REGION env var or 'us-east-1'.
        """
        self.region = region or os.environ.get('AWS_REGION', 'us-east-1')
        self.bucket_name = bucket_name or 'mystorm-results'
        self.s3_client = boto3.client('s3', region_name=self.region)
        
        # Ensure the bucket exists
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """
        Check if the bucket exists, and create it if it doesn't.
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logging.info(f"Bucket {self.bucket_name} exists")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logging.info(f"Bucket {self.bucket_name} does not exist. Creating...")
                try:
                    if self.region == 'us-east-1':
                        # Special case for us-east-1
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region}
                        )
                    logging.info(f"Bucket {self.bucket_name} created successfully")
                except ClientError as create_error:
                    logging.error(f"Failed to create bucket: {str(create_error)}")
                    raise
            else:
                logging.error(f"Error checking bucket: {str(e)}")
                raise
    
    def upload_file(self, local_file_path, s3_key=None):
        """
        Upload a file to S3.
        
        Args:
            local_file_path (str): Path to the local file
            s3_key (str, optional): S3 key to use. If None, will use the filename.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not os.path.exists(local_file_path):
            logging.error(f"File {local_file_path} does not exist")
            return False
        
        if s3_key is None:
            s3_key = os.path.basename(local_file_path)
        
        try:
            logging.info(f"Uploading {local_file_path} to s3://{self.bucket_name}/{s3_key}")
            self.s3_client.upload_file(local_file_path, self.bucket_name, s3_key)
            logging.info(f"Uploaded {local_file_path} to s3://{self.bucket_name}/{s3_key}")
            return True
        except ClientError as e:
            logging.error(f"Failed to upload {local_file_path}: {str(e)}")
            raise e
    
    def download_file(self, s3_key, local_file_path):
        """
        Download a file from S3.
        
        Args:
            s3_key (str): S3 key of the file
            local_file_path (str): Path to save the file locally
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            
            self.s3_client.download_file(self.bucket_name, s3_key, local_file_path)
            logging.info(f"Downloaded s3://{self.bucket_name}/{s3_key} to {local_file_path}")
            return True
        except ClientError as e:
            logging.error(f"Failed to download {s3_key}: {str(e)}")
            return False
    
    def upload_directory(self, local_dir_path, s3_prefix=None):
        """
        Upload an entire directory to S3.
        
        Args:
            local_dir_path (str): Path to the local directory
            s3_prefix (str, optional): S3 prefix to use. If None, will use the directory name.
        
        Returns:
            bool: True if all files were uploaded successfully, False otherwise
        """
        if not os.path.isdir(local_dir_path):
            logging.error(f"Directory {local_dir_path} does not exist")
            return False
        
        if s3_prefix is None:
            s3_prefix = os.path.basename(os.path.normpath(local_dir_path))
        
        all_successful = True
        for root, _, files in os.walk(local_dir_path):
            for file in files:
                local_file_path = os.path.join(root, file)
                # Calculate the relative path from the base directory
                relative_path = os.path.relpath(local_file_path, local_dir_path)
                s3_key = os.path.join(s3_prefix, relative_path).replace('\\', '/')
                
                if not self.upload_file(local_file_path, s3_key):
                    all_successful = False
        
        return all_successful
    
    def download_directory(self, s3_prefix, local_dir_path):
        """
        Download an entire directory from S3.
        
        Args:
            s3_prefix (str): S3 prefix of the directory
            local_dir_path (str): Path to save the directory locally
        
        Returns:
            bool: True if all files were downloaded successfully, False otherwise
        """
        try:
            # Ensure the directory exists
            os.makedirs(local_dir_path, exist_ok=True)
            
            # List all objects with the given prefix
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=s3_prefix)
            
            all_successful = True
            for page in pages:
                if 'Contents' not in page:
                    continue
                
                for obj in page['Contents']:
                    s3_key = obj['Key']
                    # Calculate the relative path from the prefix
                    if s3_key == s3_prefix:
                        continue  # Skip the prefix itself if it's listed
                    
                    relative_path = s3_key[len(s3_prefix):].lstrip('/')
                    local_file_path = os.path.join(local_dir_path, relative_path)
                    
                    # Ensure the directory exists
                    os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                    
                    if not self.download_file(s3_key, local_file_path):
                        all_successful = False
            
            return all_successful
        except ClientError as e:
            logging.error(f"Failed to download directory {s3_prefix}: {str(e)}")
            return False
    
    def list_files(self, s3_prefix=""):
        """
        List all files in the bucket with the given prefix.
        
        Args:
            s3_prefix (str, optional): S3 prefix to list. Default is empty string (list all).
        
        Returns:
            list: List of S3 keys
        """
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=s3_prefix)
            
            result = []
            for page in pages:
                if 'Contents' not in page:
                    continue
                
                for obj in page['Contents']:
                    result.append(obj['Key'])
            
            return result
        except ClientError as e:
            logging.error(f"Failed to list files with prefix {s3_prefix}: {str(e)}")
            return []
    
    def delete_file(self, s3_key):
        """
        Delete a file from S3.
        
        Args:
            s3_key (str): S3 key of the file
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logging.info(f"Deleted s3://{self.bucket_name}/{s3_key}")
            return True
        except ClientError as e:
            logging.error(f"Failed to delete {s3_key}: {str(e)}")
            return False
    
    def delete_directory(self, s3_prefix):
        """
        Delete an entire directory from S3.
        
        Args:
            s3_prefix (str): S3 prefix of the directory
        
        Returns:
            bool: True if all files were deleted successfully, False otherwise
        """
        try:
            # List all objects with the given prefix
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=s3_prefix)
            
            all_successful = True
            for page in pages:
                if 'Contents' not in page:
                    continue
                
                objects_to_delete = [{'Key': obj['Key']} for obj in page['Contents']]
                if objects_to_delete:
                    self.s3_client.delete_objects(
                        Bucket=self.bucket_name,
                        Delete={'Objects': objects_to_delete}
                    )
            
            return all_successful
        except ClientError as e:
            logging.error(f"Failed to delete directory {s3_prefix}: {str(e)}")
            return False
    
    def get_s3_url(self, s3_key):
        """
        Get the S3 URL for a file.
        
        Args:
            s3_key (str): S3 key of the file
        
        Returns:
            str: S3 URL
        """
        return f"s3://{self.bucket_name}/{s3_key}"
    
    def get_presigned_url(self, s3_key, expiration=3600):
        """
        Generate a presigned URL for a file.
        
        Args:
            s3_key (str): S3 key of the file
            expiration (int, optional): URL expiration time in seconds. Default is 1 hour.
        
        Returns:
            str: Presigned URL or None if failed
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logging.error(f"Failed to generate presigned URL for {s3_key}: {str(e)}")
            return None
