"""
Azure Blob Storage operations for saving chunked content as JSON.
"""
import json
from datetime import datetime
from typing import List, Optional

from azure.storage.blob import BlobServiceClient
from logger import StructuredLogger

logger = StructuredLogger(__name__)


class BlobStorage:
    """Handles storage of processed content to Azure Blob Storage."""
    
    def __init__(self, connection_string: str, container_name: str = "scraped-content"):
        """
        Initialize Blob Storage client.
        
        Args:
            connection_string: Azure Storage connection string
            container_name: Container name for storing content
        """
        self.connection_string = connection_string
        self.container_name = container_name
        
        try:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                connection_string
            )
            # Ensure container exists
            container_client = self.blob_service_client.get_container_client(
                container_name
            )
            container_client.get_container_properties()
            logger.info("Blob Storage connected", {
                "container": container_name
            })
        except Exception as e:
            logger.error("Blob Storage connection failed", {
                "container": container_name,
                "error": str(e)
            })
            raise
    
    def save_documents(
        self,
        url: str,
        url_hash: str,
        documents: List[dict]
    ) -> Optional[str]:
        """
        Save search documents to blob storage as JSON.
        
        Args:
            url: Source URL
            url_hash: Hash identifier
            documents: List of search documents to save
        
        Returns:
            Blob name if successful, None otherwise
        """
        try:
            # Create blob name from URL hash and timestamp
            timestamp = datetime.utcnow().isoformat().replace(":", "-").split(".")[0]
            blob_name = f"documents/{url_hash}/{timestamp}.json"
            
            # Prepare content
            output = {
                "source_url": url,
                "processed_at": datetime.utcnow().isoformat(),
                "document_count": len(documents),
                "documents": documents
            }
            
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Upload JSON
            blob_client.upload_blob(
                json.dumps(output, indent=2),
                overwrite=True
            )
            
            logger.info("Documents saved to Blob Storage", {
                "url_hash": url_hash,
                "blob_name": blob_name,
                "document_count": len(documents)
            })
            
            return blob_name
        
        except Exception as e:
            logger.error("Blob Storage save failed", {
                "url_hash": url_hash,
                "url": url,
                "error": str(e)
            })
            return None
    
    def list_processed_urls(self) -> List[dict]:
        """
        List all processed URLs stored in Blob Storage.
        
        Returns:
            List of dicts with url_hash, latest_file, document_count
        """
        try:
            container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            
            urls_map = {}
            
            for blob in container_client.list_blobs(name_starts_with="documents/"):
                parts = blob.name.split("/")
                if len(parts) >= 3:
                    url_hash = parts[1]
                    if url_hash not in urls_map:
                        urls_map[url_hash] = {
                            "url_hash": url_hash,
                            "latest_file": blob.name,
                            "last_modified": blob.last_modified.isoformat()
                        }
            
            logger.info("Listed processed URLs", {
                "url_count": len(urls_map)
            })
            
            return list(urls_map.values())
        
        except Exception as e:
            logger.error("Failed to list processed URLs", {
                "error": str(e)
            })
            return []
    
    def get_document(self, blob_name: str) -> Optional[dict]:
        """
        Retrieve a previously processed document.
        
        Args:
            blob_name: Name of the blob file
        
        Returns:
            Parsed JSON document or None
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            content = blob_client.download_blob().readall()
            return json.loads(content)
        
        except Exception as e:
            logger.error("Failed to retrieve document", {
                "blob_name": blob_name,
                "error": str(e)
            })
            return None
