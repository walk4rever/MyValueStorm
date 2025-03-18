"""
S3 Storage module for MyValueStorm project.
This module provides functionality for storing and retrieving files from AWS S3.
"""

import os
import logging
import boto3
from botocore.exceptions import ClientError
from typing import Optional, List, Union

class S3Storage:
    """
    Class for handling S3 storage operations.
    """
    
    def __init__(self, 
                 bucket_name: Optional[str] = None, 
                 region: Optional[str] = None):
        """
        Initialize S3 storage.
        
        Args:
            bucket_name (str, optional): S3 bucket name
            region (str, optional): AWS region
        """
        self.bucket_name = bucket_name or os.environ.get("S3_BUCKET", "mystorm-results")
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        
        # Initialize S3 client
        self.s3_client = boto3.client('s3', region_name=self.region)
        
        # Ensure bucket exists
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self) -> bool:
        """
        Ensure the S3 bucket exists, create if it doesn't.
        
        Returns:
            bool: True if bucket exists or was created, False otherwise
        """
        try:
            # Check if bucket exists
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            
            # If bucket doesn't exist, create it
            if error_code == '404':
                try:
                    # Create bucket with appropriate configuration
                    if self.region == 'us-east-1':
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        location = {'LocationConstraint': self.region}
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration=location
                        )
                    logging.info(f"Created S3 bucket: {self.bucket_name}")
                    return True
                except Exception as create_error:
                    logging.error(f"Failed to create S3 bucket: {str(create_error)}")
                    return False
            else:
                logging.error(f"Error accessing S3 bucket: {str(e)}")
                return False
    
    def upload_file(self, local_path: str, s3_key: str) -> bool:
        """
        Upload a file to S3.
        
        Args:
            local_path (str): Path to local file
            s3_key (str): S3 object key
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.s3_client.upload_file(local_path, self.bucket_name, s3_key)
            logging.info(f"Uploaded {local_path} to s3://{self.bucket_name}/{s3_key}")
            return True
        except Exception as e:
            logging.error(f"Error uploading file to S3: {str(e)}")
            return False
    
    def download_file(self, s3_key: str, local_path: Optional[str] = None) -> Union[str, bool]:
        """
        Download a file from S3.
        
        Args:
            s3_key (str): S3 object key
            local_path (str, optional): Path to save file locally
            
        Returns:
            Union[str, bool]: File content as string if local_path is None, 
                             True if downloaded to local_path, False if failed
        """
        try:
            if local_path:
                # Ensure directory exists
                os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
                
                # Download to file
                self.s3_client.download_file(self.bucket_name, s3_key, local_path)
                logging.info(f"Downloaded s3://{self.bucket_name}/{s3_key} to {local_path}")
                return True
            else:
                # Download to memory
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
                return response['Body'].read().decode('utf-8')
        except Exception as e:
            logging.error(f"Error downloading file from S3: {str(e)}")
            return False if local_path else ""
    
    def list_files(self, prefix: str = "") -> List[str]:
        """
        List files in S3 bucket with given prefix.
        
        Args:
            prefix (str): S3 key prefix
            
        Returns:
            List[str]: List of S3 keys
        """
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            
            if 'Contents' in response:
                return [item['Key'] for item in response['Contents']]
            return []
        except Exception as e:
            logging.error(f"Error listing files in S3: {str(e)}")
            return []
    
    def list_directories(self, prefix: str = "") -> List[str]:
        """
        List directories (common prefixes) in S3 bucket.
        
        Args:
            prefix (str): S3 key prefix
            
        Returns:
            List[str]: List of directory names
        """
        try:
            # Add trailing slash if not present and not empty
            if prefix and not prefix.endswith('/'):
                prefix += '/'
                
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                Delimiter='/'
            )
            
            directories = []
            
            # Get common prefixes (directories)
            if 'CommonPrefixes' in response:
                for obj in response['CommonPrefixes']:
                    # Remove trailing slash and prefix
                    dir_name = obj['Prefix']
                    if dir_name.endswith('/'):
                        dir_name = dir_name[:-1]
                    if prefix and dir_name.startswith(prefix):
                        dir_name = dir_name[len(prefix):]
                    directories.append(dir_name)
            
            return directories
        except Exception as e:
            logging.error(f"Error listing directories in S3: {str(e)}")
            return []
    
    def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3.
        
        Args:
            s3_key (str): S3 object key
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logging.info(f"Deleted s3://{self.bucket_name}/{s3_key}")
            return True
        except Exception as e:
            logging.error(f"Error deleting file from S3: {str(e)}")
            return False
    
    def delete_directory(self, prefix: str) -> bool:
        """
        Delete all files with given prefix from S3.
        
        Args:
            prefix (str): S3 key prefix
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Add trailing slash if not present and not empty
            if prefix and not prefix.endswith('/'):
                prefix += '/'
                
            # List all objects with the prefix
            objects_to_delete = self.list_files(prefix)
            
            if not objects_to_delete:
                return True
                
            # Delete objects in batches of 1000 (S3 limit)
            batch_size = 1000
            for i in range(0, len(objects_to_delete), batch_size):
                batch = objects_to_delete[i:i+batch_size]
                
                delete_dict = {
                    'Objects': [{'Key': key} for key in batch],
                    'Quiet': True
                }
                
                self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete=delete_dict
                )
            
            logging.info(f"Deleted {len(objects_to_delete)} objects with prefix {prefix}")
            return True
        except Exception as e:
            logging.error(f"Error deleting directory from S3: {str(e)}")
            return False
