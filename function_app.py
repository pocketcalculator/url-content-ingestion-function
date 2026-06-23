"""
Azure Function for web scraping and content processing.
Triggered via HTTP request with URL parameter.

Example request:
  POST /api/scrape-url
  Content-Type: application/json
  
  {
    "url": "https://example.com/article",
    "upload_to_blob": true
  }

Response:
  {
    "status": "success",
    "url": "https://example.com/article",
    "documents_created": 5,
    "blob_name": "documents/a1b2c3d4/2026-06-09T10-30-45.json"
  }
"""
import asyncio
import json
import os
from typing import Optional

import azure.functions as func

from chunker import TextChunker
from logger import StructuredLogger
from scraper import ContentScraper
from storage import BlobStorage

logger = StructuredLogger(__name__)


async def scrape_url_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main handler for URL scraping requests.
    
    Expected JSON body:
    {
        "url": "https://example.com",
        "upload_to_blob": true
    }
    """
    try:
        # Parse request
        req_body = req.get_json()
        url = req_body.get("url")
        upload_to_blob = req_body.get("upload_to_blob", True)
        
        if not url:
            return func.HttpResponse(
                json.dumps({"error": "Missing 'url' parameter"}),
                status_code=400,
                mimetype="application/json"
            )
        
        logger.info("Scrape request received", {
            "url": url,
            "upload_to_blob": upload_to_blob
        })
        
        # Scrape content
        scraper = ContentScraper()
        scraped_data = await scraper.scrape(url)
        
        if not scraped_data:
            return func.HttpResponse(
                json.dumps({
                    "status": "failed",
                    "url": url,
                    "error": "Failed to scrape URL content"
                }),
                status_code=500,
                mimetype="application/json"
            )
        
        # Chunk content
        chunks = TextChunker.chunk_text(scraped_data["content"])
        documents = TextChunker.create_search_documents(
            url=scraped_data["url"],
            url_hash=scraped_data["url_hash"],
            title=scraped_data["metadata"]["title"],
            chunks=chunks
        )
        
        logger.info("Content processed", {
            "url": url,
            "chunk_count": len(chunks),
            "document_count": len(documents)
        })
        
        response_data = {
            "status": "success",
            "url": url,
            "documents_created": len(documents),
            "title": scraped_data["metadata"]["title"],
            "content_length": len(scraped_data["content"]),
            "chunks": len(chunks),
        }
        
        # Upload to Blob Storage if requested
        blob_name = None
        if upload_to_blob:
            try:
                conn_string = os.environ.get("AzureWebJobsStorage")
                if not conn_string:
                    logger.warning("Azure Storage connection not configured")
                else:
                    storage = BlobStorage(conn_string)
                    blob_name = storage.save_documents(
                        url=scraped_data["url"],
                        url_hash=scraped_data["url_hash"],
                        documents=documents
                    )
                    response_data["blob_name"] = blob_name
            except Exception as e:
                logger.error("Blob storage upload failed", {
                    "url": url,
                    "error": str(e)
                })
                response_data["blob_upload_error"] = str(e)
        
        logger.info("Scrape completed successfully", {
            "url": url,
            "documents_created": len(documents),
            "blob_stored": blob_name is not None
        })
        
        return func.HttpResponse(
            json.dumps(response_data, indent=2),
            status_code=200,
            mimetype="application/json"
        )
    
    except ValueError as e:
        logger.error("Invalid request format", {"error": str(e)})
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON format"}),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error("Unexpected error", {"error": str(e)})
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "error": str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )


# Azure Function app
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(route="scrape-url", methods=["POST"])
async def scrape_url(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP trigger for scraping URLs."""
    return await scrape_url_handler(req)


@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
    return func.HttpResponse(
        json.dumps({"status": "healthy"}),
        status_code=200,
        mimetype="application/json"
    )
