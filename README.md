# Azure AI Search URL Ingestion Function

A production-ready Azure Function that scrapes URLs, extracts clean content, intelligently chunks text, and prepares optimized JSON documents for Azure AI Search indexing.

## Features

✅ **Dual-Mode Scraping**
- **Playwright** for JavaScript-heavy sites with headless browser rendering
- **Fallback to requests + BeautifulSoup** for simple static sites
- Automatic method selection based on content type

✅ **Intelligent Content Extraction**
- Uses **trafilatura** for accurate main content extraction
- Removes noise: ads, navigation, footers, scripts
- Preserves document structure and semantics
- Extracts metadata: title, author, date

✅ **Smart Text Chunking**
- Chunks maintain paragraph/sentence boundaries for semantic coherence
- Configurable chunk sizes optimized for Azure AI Search (~1.5KB per chunk)
- Preserves context across chunks
- Handles edge cases: very long paragraphs, short content

✅ **Azure Integration**
- Saves processed content to **Azure Blob Storage** as JSON
- Documents pre-formatted for direct AI Search indexing
- Structured logging for debugging
- Error handling with graceful degradation

✅ **Error Handling**
- Timeout handling (30 seconds per request)
- Automatic retry logic with fallback methods
- Detailed structured logging
- Validation at each pipeline stage

## Architecture

```
Input: URL
  ↓
[Playwright Renderer]  ← For JavaScript-heavy sites
  ↓ (fallback)
[Requests + BeautifulSoup]  ← For static sites
  ↓
[Content Extraction]  ← Trafilatura + fallback
  ↓
[Content Filtering]  ← Remove noise
  ↓
[Text Chunking]  ← Semantic-aware chunking
  ↓
[Document Generation]  ← JSON for AI Search
  ↓
[Blob Storage]  ← Persist for later indexing
  ↓
Output: JSON documents ready for AI Search
```

## File Structure

```
.
├── function_app.py          # Azure Function entry point
├── scraper.py              # Web scraping & content extraction
├── chunker.py              # Intelligent text chunking
├── storage.py              # Azure Blob Storage operations
├── logger.py               # Structured logging
├── requirements.txt        # Python dependencies
├── local.settings.json     # Local dev configuration
└── README.md              # This file
```

## Setup

### Prerequisites

- Python 3.10+
- Azure Storage Account (for blob storage)
- Azure Functions Core Tools

### Local Development

1. **Clone and navigate to project**
```bash
cd <your-project-folder>
```

2. **Create Python virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Install Playwright browsers** (one-time)
```bash
playwright install chromium
```

5. **Configure local.settings.json**
```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "DefaultEndpointsProtocol=https;AccountName=YOUR_STORAGE_ACCOUNT;AccountKey=YOUR_KEY;EndpointSuffix=core.windows.net",
    "FUNCTIONS_WORKER_RUNTIME": "python"
  }
}
```

6. **Run locally**
```bash
func start
```

The function will be available at: `http://localhost:7071/api/scrape-url`

## API Usage

### Endpoint

```
POST /api/scrape-url
Content-Type: application/json
```

### Request Body

```json
{
  "url": "https://example.com/article",
  "upload_to_blob": true
}
```

**Parameters:**
- `url` (required): The URL to scrape
- `upload_to_blob` (optional, default: true): Save documents to Azure Blob Storage

### Example cURL Request

```bash
curl -X POST http://localhost:7071/api/scrape-url \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://en.wikipedia.org/wiki/Azure",
    "upload_to_blob": true
  }'
```

### Response

```json
{
  "status": "success",
  "url": "https://en.wikipedia.org/wiki/Azure",
  "documents_created": 8,
  "title": "Azure - Wikipedia",
  "content_length": 12450,
  "chunks": 8,
  "blob_name": "documents/a1b2c3d4/2026-06-09T10-30-45.json"
}
```

### Success Response (HTTP 200)
```json
{
  "status": "success",
  "url": "...",
  "documents_created": 5,
  "title": "...",
  "content_length": 5000,
  "chunks": 5,
  "blob_name": "documents/hash/timestamp.json"
}
```

### Error Responses

**Invalid URL (HTTP 400)**
```json
{
  "error": "Missing 'url' parameter"
}
```

**Scrape Failed (HTTP 500)**
```json
{
  "status": "failed",
  "url": "...",
  "error": "Failed to scrape URL content"
}
```

**Storage Error (HTTP 200 with warning)**
```json
{
  "status": "success",
  "documents_created": 5,
  "blob_upload_error": "Connection failed"
}
```

## Output Format

### Blob Storage JSON Structure

Stored at: `documents/{url_hash}/{timestamp}.json`

```json
{
  "source_url": "https://example.com/article",
  "processed_at": "2026-06-09T10:30:45.123456",
  "document_count": 5,
  "documents": [
    {
      "id": "a1b2c3d4_chunk_001",
      "source_url": "https://example.com/article",
      "url_hash": "a1b2c3d4",
      "title": "Article Title",
      "chunk_number": 1,
      "total_chunks": 5,
      "content": "First chunk of content..."
    },
    {
      "id": "a1b2c3d4_chunk_002",
      "source_url": "https://example.com/article",
      "url_hash": "a1b2c3d4",
      "title": "Article Title",
      "chunk_number": 2,
      "total_chunks": 5,
      "content": "Second chunk of content..."
    }
  ]
}
```

## Azure AI Search Integration

### Option 1: Manual Indexing (Current)

1. Retrieve JSON from blob storage
2. Create Azure AI Search index with fields:
   - `id` (key)
   - `source_url` (searchable, filterable)
   - `url_hash` (filterable)
   - `title` (searchable)
   - `chunk_number` (filterable)
   - `total_chunks` (filterable)
   - `content` (searchable)

3. Upload documents to index

### Option 2: Automated Indexing (Future Enhancement)

Can add blob storage trigger to automatically index documents as they're created.

## Configuration

### Chunking Parameters

Edit `chunker.py`:
```python
TARGET_CHUNK_SIZE = 1500   # Target chunk size in characters
MIN_CHUNK_SIZE = 200       # Minimum meaningful chunk
MAX_CHUNK_SIZE = 2500      # Maximum per field
```

### Scraping Timeout

Edit `scraper.py`:
```python
TIMEOUT_SECONDS = 30       # Request timeout
```

### Content Filters

Edit `scraper.py` `_extract_with_beautifulsoup()` to customize noise removal:
```python
for script in soup(["script", "style", "nav", "footer", "noscript"]):
    script.decompose()
```

## Error Handling & Logging

All errors are logged with structured context:

```json
{
  "timestamp": "2026-06-09T10:30:45.123456",
  "level": "ERROR",
  "message": "Content extraction failed",
  "url": "https://example.com",
  "url_hash": "a1b2c3d4",
  "error": "Connection timeout"
}
```

Check Azure Functions logs for debugging:
- Local: Terminal output during `func start`
- Azure: Application Insights / Azure Monitor

## Limitations & Considerations

- **JavaScript Rendering Cost**: Playwright adds ~5-10 seconds per request. For large-scale scraping, consider queue-based processing.
- **Memory Usage**: Playwright browser instances use significant memory. Consider Azure Function Premium plan for concurrent requests.
- **Rate Limiting**: Implement backoff for target sites to avoid being blocked.
- **Legal Compliance**: Always check target site's `robots.txt` and terms of service.
- **Maximum Execution Time**: Azure Functions have 10-minute timeout by default; optimize large content processing.

## Performance Tips

1. **Content Size**: Very large documents (>1MB) may hit limits. Consider pre-filtering.
2. **Parallel Processing**: Use async Azure Function invocations for multiple URLs.
3. **Caching**: Implement blob storage caching to avoid re-scraping identical URLs.
4. **Headless Browser**: Disable Playwright for known static-only sites to save resources.

## Deployment to Azure

1. **Create Azure Function App**
```bash
az functionapp create --resource-group myResourceGroup \
  --consumption-plan-location eastus \
  --runtime python --runtime-version 3.11 \
  --functions-version 4 \
  --name myScrapeFunction
```

2. **Deploy code**
```bash
func azure functionapp publish myScrapeFunction
```

3. **Configure App Settings**
```bash
az functionapp config appsettings set \
  --name myScrapeFunction \
  --resource-group myResourceGroup \
  --settings AzureWebJobsStorage="<connection_string>"
```

4. **Invoke via HTTPS**
```bash
curl -X POST https://myScrapeFunction.azurewebsites.net/api/scrape-url \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com"}'
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| azure-functions | 1.19.0 | Azure Functions framework |
| azure-storage-blob | 12.19.0 | Blob storage operations |
| playwright | 1.46.0 | Headless browser for JS sites |
| beautifulsoup4 | 4.12.3 | HTML parsing fallback |
| trafilatura | 1.8.0 | Content extraction |
| requests | 2.32.3 | HTTP requests |

## Health Check

```bash
curl http://localhost:7071/api/health
```

Response:
```json
{
  "status": "healthy"
}
```

## Troubleshooting

### Playwright Installation Issues

**Error**: `Executable does not exist at /path/to/chromium`

**Solution**:
```bash
playwright install chromium
```

### Blob Storage Connection Failed

**Error**: `BlobServiceClient connection failed`

**Solution**:
- Verify connection string in `local.settings.json`
- Run Azure Storage Emulator or use real storage account
- Check network connectivity

### Content Extraction Returns Empty

**Possible causes**:
- JavaScript-required content not rendering (check Playwright logs)
- Content behind authentication
- Dynamic content loading
- Site blocking automated requests

**Solutions**:
- Add custom User-Agent in `scraper.py`
- Increase timeout for slow sites
- Implement authentication if needed
- Add delay between requests

## Contributing

To extend functionality:

1. Add new extraction method: Extend `ContentScraper` class
2. Custom chunking strategy: Subclass `TextChunker`
3. Additional storage backends: Implement `BlobStorage` interface
4. Custom metadata extraction: Modify `trafilatura` configuration

## License

MIT License - See LICENSE file

## Support

For issues:
1. Check structured logs in Azure Monitor
2. Verify configuration in `local.settings.json`
3. Test with simple URLs first (e.g., Wikipedia)
4. Check URL accessibility in browser
