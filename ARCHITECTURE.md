# Architecture & Design Decisions

## Overview

This Azure Function implements a robust URL scraping pipeline optimized for Azure AI Search indexing. The architecture prioritizes reliability, content quality, and scalability.

## Design Principles

1. **Defense in Depth**: Multiple fallback mechanisms at each stage
2. **Semantic Coherence**: Preserve document structure during chunking
3. **Observability**: Structured logging throughout the pipeline
4. **Separation of Concerns**: Modular design with single responsibility
5. **Azure-Native**: Leverage Azure services for storage and integration

## Component Architecture

### 1. Content Scraper (`scraper.py`)

**Purpose**: Fetch and extract clean content from URLs

**Design Decisions**:

#### Dual-Mode Scraping
- **Playwright**: Primary method for JavaScript-heavy sites
  - Renders JavaScript before content extraction
  - More resource-intensive (5-10 seconds per request)
  - Suitable for modern SPAs and dynamic content
  
- **Requests + BeautifulSoup**: Fallback for static sites
  - Fast and lightweight
  - Fails gracefully on dynamic content
  - Automatic fallback improves success rate

```
┌─────────────┐
│ Fetch URL   │
└──────┬──────┘
       │
       ├─→ [Playwright] ─→ Success? ──→ Continue
       │        ↓ timeout/error
       │
       ├─→ [Requests] ─→ Success? ──→ Continue
       │       ↓ failed
       │
       └─→ Return None (all methods failed)
```

#### Content Extraction: Trafilatura + BeautifulSoup
- **Trafilatura**: State-of-the-art content extraction
  - Removes ads, navigation, sidebars automatically
  - ~95% accuracy on main content extraction
  - Extracts metadata (title, author, date)
  
- **BeautifulSoup Fallback**: If trafilatura fails
  - Manual removal of `<script>`, `<style>`, `<nav>`, `<footer>`
  - Simpler but more reliable for edge cases

**Error Handling**:
```python
if trafilatura_works:
    use trafilatura
else if beautifulsoup_works:
    use beautifulsoup (minimal filtering)
else:
    log error and fail gracefully
```

**URL Validation**:
- Uses `urllib.parse` to validate URL structure
- Rejects malformed URLs before scraping
- Prevents DNS resolution attacks

### 2. Text Chunker (`chunker.py`)

**Purpose**: Split content into semantically coherent chunks for AI Search

**Design Decisions**:

#### Why Intelligent Chunking?

AI Search performs best when documents:
- Are under 2000 characters per searchable field
- Maintain semantic coherence (don't split mid-paragraph)
- Preserve context (chunk numbering helps with reassembly)

#### Three-Level Hierarchy

```
                   Text (>1500 chars)
                         │
                    ┌────┴─────┐
                    ↓          ↓
            Paragraph1    Paragraph2
            (800 chars)    (2500 chars)
                             │
                        ┌────┴───┐
                        ↓        ↓
                    Sentence1  Sentence2
                    (300ch)    (1200ch)
                         ↓
                    [Chunk 1: 300ch]
                    [Chunk 2: 1200ch]
```

**Algorithm**:

1. **First Attempt**: Add entire paragraphs while under limit
2. **If Paragraph Too Large**: Split by sentences
3. **If Sentence Too Large**: Keep as-is (single sentence chunk)
4. **Validation**: Discard chunks <200 chars or >2500 chars

**Advantages**:
- ✅ Preserves paragraph structure
- ✅ Maintains sentence coherence
- ✅ Optimizes for search relevance
- ✅ Handles edge cases (long paragraphs, short articles)

**Chunk Metadata**:
```json
{
  "id": "a1b2c3d4_chunk_001",
  "chunk_number": 1,
  "total_chunks": 5,  // Enables reconstructing full document
  "source_url": "...",
  "content": "..."
}
```

### 3. Blob Storage (`storage.py`)

**Purpose**: Persist processed documents for later indexing

**Design Decisions**:

#### Storage Structure

```
Container: scraped-content/
    └── documents/
        └── {url_hash}/
            ├── 2026-06-09T10-30-45.json
            ├── 2026-06-09T11-45-22.json
            └── 2026-06-09T14-12-03.json
```

**Benefits**:
- ✅ Organized by content source (url_hash)
- ✅ Time-series tracking of scrapes
- ✅ Easy re-indexing with versioning
- ✅ Supports deduplication logic

#### Document Format: JSON

**Why JSON over Text/Markdown?**

| Format | Pros | Cons |
|--------|------|------|
| **JSON** | Structured, filterable, direct AI Search integration | Slightly more verbose |
| **Markdown** | Human-readable, preserves structure | Loses structured metadata |
| **Plain Text** | Simplest, smallest | No metadata, poor search quality |

**Decision**: JSON wins for production use because:
1. Azure AI Search natively understands JSON fields
2. Field-level filtering and boosting in search
3. Structured metadata enables advanced queries
4. Direct programmatic indexing without parsing

**JSON Structure**:
```json
{
  "id": "a1b2c3d4_chunk_001",           // Unique identifier
  "source_url": "...",                   // Traceable to original
  "url_hash": "a1b2c3d4",               // Grouping key
  "title": "Article Title",              // Searchable
  "chunk_number": 1,                     // Ordering
  "total_chunks": 5,                     // Context
  "content": "..."                       // Searchable body
}
```

#### Naming Strategy

```
documents/{url_hash}/{YYYY-MM-DDTHH-MM-SS}.json
  │         │           │
  │         │           └─ UTC timestamp (sortable)
  │         └─────────────── MD5 hash of URL (8 chars, collision-free)
  └─────────────────────────── Folder hierarchy for organization
```

**Advantages**:
- Easy to identify URL from blob name
- Chronological ordering of versions
- No special characters that break file systems
- Prevents conflicts with concurrent uploads

### 4. Logging (`logger.py`)

**Purpose**: Structured observability for debugging

**Design Decisions**:

#### Structured Logging

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

**Benefits**:
- ✅ Machine-parseable (JSON)
- ✅ Queryable in Azure Monitor
- ✅ Context included automatically
- ✅ Supports distributed tracing

#### Log Levels

- `INFO`: Normal operation (scrape started, chunks created)
- `WARNING`: Fallback paths taken (playwright failed, using requests)
- `ERROR`: Unrecoverable failures (all methods failed)

### 5. Azure Function App (`function_app.py`)

**Purpose**: Orchestrate components and expose HTTP API

**Design Decisions**:

#### Request/Response Pattern

```
REQUEST
{
  "url": "...",              // Required
  "upload_to_blob": true     // Optional (default: true)
}
      ↓
  [Validate URL]
      ↓
  [Scrape Content]
      ↓
  [Extract Content]
      ↓
  [Chunk Text]
      ↓
  [Generate Docs]
      ↓
  [Upload to Blob]
      ↓
RESPONSE
{
  "status": "success",
  "documents_created": 5,
  "blob_name": "...",
  ...
}
```

#### Error Handling Strategy

**Graceful Degradation**: Function doesn't fail if blob upload fails

```python
try:
    scrape()           # ← Must succeed
    chunk()            # ← Must succeed
    generate_docs()    # ← Must succeed
    upload_blob()      # ← OK if fails (logged as warning)
except:
    return error_response()
```

**Rationale**: Documents are generated in-memory. If blob upload fails, return success with warning so client can retry. Prevents cascading failures.

#### HTTP Status Codes

- `200 OK`: Scraping succeeded (even if blob upload failed)
- `400 Bad Request`: Invalid input (missing URL, malformed JSON)
- `500 Server Error`: Unrecoverable error (scraping failed completely)

#### Async/Await Pattern

```python
async def scrape_url_handler(req):
    scraper = ContentScraper()
    scraped_data = await scraper.scrape(url)  # Awaits Playwright
    # ... rest of sync operations
    return response
```

**Design**: 
- Scraper is async-friendly (Playwright is async)
- Handler awaits scraper
- Storage operations are sync (Azure SDK)
- Total latency: ~5-15 seconds (mostly Playwright)

## Data Flow Diagram

```
Client Request
    │
    ├─→ [Validate URL]
    │       ↓
    │   Invalid? → 400 Error
    │       │ Valid
    │       ↓
    ├─→ [Fetch HTML]
    │       ├─→ Playwright
    │       │   ↓ timeout
    │       └─→ Requests
    │           ↓ failed
    │           → 500 Error
    │       │ Success
    │       ↓
    ├─→ [Extract Content]
    │       ├─→ Trafilatura
    │       │   ↓ failed
    │       └─→ BeautifulSoup
    │           ↓ failed
    │           → 500 Error
    │       │ Success
    │       ↓
    ├─→ [Filter Content]
    │       ↓ remove noise
    │       → cleaned text
    │       ↓
    ├─→ [Chunk Text]
    │       ├─→ Split by paragraph
    │       │   ├─→ Too large?
    │       │   │   ├─→ Split by sentence
    │       │   │   │   ├─→ Too large?
    │       │   │   │   │   └─→ Keep as-is
    │       │   │   │   └─→ [Chunk]
    │       │   │   └─→ [Chunk]
    │       │   └─→ [Chunk]
    │       └─→ [Chunks...]
    │       ↓
    ├─→ [Create Docs]
    │       └─→ JSON documents with metadata
    │       ↓
    ├─→ [Upload to Blob]
    │       ├─→ Success → Include blob_name
    │       └─→ Failed → Include error warning
    │       ↓
    └─→ Return 200 with metadata
```

## Failure Modes & Recovery

### Mode 1: URL Unreachable
**Scenario**: Target server offline or DNS fails
**Handling**: Both Playwright and Requests will timeout after 30s
**Result**: Return 500 with descriptive error

### Mode 2: JavaScript Rendering Required But Fails
**Scenario**: Playwright times out or crashes
**Handling**: Fallback to Requests (gets partial content)
**Result**: May get empty content; return 500

### Mode 3: Content Extraction Returns Empty
**Scenario**: Page is JavaScript-generated and not rendered
**Handling**: Log detailed error with URL
**Result**: Return 500; client can retry or use different approach

### Mode 4: Blob Upload Fails (Network Error)
**Scenario**: Azure Storage temporarily unavailable
**Handling**: Log warning; return 200 with error notification
**Result**: Documents available in-memory; client can save locally or retry

### Mode 5: Very Large Content (>10MB)
**Scenario**: Wikipedia-scale articles
**Handling**: Process as-is, chunk normally, may create 100+ chunks
**Result**: Success; depends on AI Search index limits

## Performance Considerations

### Latency Breakdown (Typical)
```
Playwright fetch:          5-8 seconds   (browser startup + render)
Requests fetch:            1-2 seconds   (HTML download only)
Content extraction:        500ms         (parsing + filtering)
Text chunking:             50ms          (algorithmic)
Blob upload:               1-2 seconds   (network I/O)
─────────────────────────────────────────
Total (Playwright path):   ~7-13 seconds
Total (Requests path):     ~3-5 seconds
```

### Memory Usage
```
Browser instance:          ~100-150 MB   (Playwright)
HTML content:              ~5-50 MB      (typical pages)
Parsed content:            ~1-10 MB      (after filtering)
──────────────────────────────────────
Total per request:         ~110-210 MB
```

**Implication**: For concurrent requests, consider Azure Premium Functions plan.

### Optimization Strategies

1. **Caching**: Store recently scraped URLs to avoid re-fetching
2. **Queue Processing**: Use Azure Service Bus for batch processing
3. **Browser Pooling**: Reuse browser instances across requests
4. **Streaming**: For very large content, stream to blob instead of buffering

## Scalability Path

```
Current Architecture (Low Volume)
    ├─ Single HTTP trigger
    ├─ Per-request scraping
    └─ ~5-15s latency per URL

Recommended for Medium Volume (100+ URLs/day)
    ├─ Service Bus queue trigger
    ├─ Batch processing (10-50 URLs)
    ├─ Parallel Playwright instances
    └─ Durable Functions for orchestration

Recommended for High Volume (1000+ URLs/day)
    ├─ Event Grid + Event Hub
    ├─ Container instances (Docker)
    ├─ Browser pool with load balancing
    ├─ Distributed caching (Redis)
    └─ Blob Storage tier with lifecycle policies
```

## Security Considerations

1. **Input Validation**: URL schema and netloc verified
2. **Timeout Protection**: 30s timeout prevents resource exhaustion
3. **Blob Access**: Use Managed Identity for Azure Auth (no connection strings in code)
4. **Rate Limiting**: Not implemented; recommend API Management for production
5. **Content Filtering**: Removes scripts but doesn't sanitize for execution

**Recommendations**:
- Use Azure API Management for rate limiting
- Store secrets in Key Vault, not `local.settings.json`
- Use Managed Identity for all Azure services
- Enable audit logging for Blob Storage
- Implement virus scanning for extracted content if needed

## Future Enhancements

1. **Caching Layer**: Redis for URL deduplication
2. **Direct AI Search Integration**: Eliminate blob storage, index directly
3. **Webhook Triggers**: Event Grid for continuous crawling
4. **Advanced Filtering**: NLP-based noise removal
5. **Multi-language Support**: Language detection and handling
6. **Authentication**: Handle login-required content via Playwright
7. **Screenshot Capture**: Extract visual content alongside text
8. **Link Extraction**: Build site graph from discovered URLs
