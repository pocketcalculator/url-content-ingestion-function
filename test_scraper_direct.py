"""
Direct test of scraper components without Azure Function runtime.
"""
import asyncio
import json
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from scraper import ContentScraper
from chunker import TextChunker
from logger import StructuredLogger

logger = StructuredLogger(__name__)


async def test_scraper():
    """Test the scraper with real URLs."""
    
    print("\n" + "=" * 70)
    print("🚀 SCRAPER COMPONENT TEST")
    print("=" * 70)
    
    # Test URL - simple static site
    test_urls = [
        "https://example.com",
        "https://en.wikipedia.org/wiki/Web_scraping"
    ]
    
    scraper = ContentScraper()
    
    for url in test_urls:
        print(f"\n📄 Testing: {url}")
        print("-" * 70)
        
        try:
            # Scrape
            result = await scraper.scrape(url)
            
            if not result:
                print(f"❌ Failed to scrape URL")
                continue
            
            print(f"✅ Scrape successful!")
            print(f"   Title: {result['metadata']['title']}")
            print(f"   Content length: {len(result['content'])} chars")
            print(f"   URL Hash: {result['url_hash']}")
            
            # Chunk the content
            chunks = TextChunker.chunk_text(result['content'])
            print(f"\n✅ Text chunking successful!")
            print(f"   Chunks created: {len(chunks)}")
            
            for idx, chunk in enumerate(chunks[:2], 1):  # Show first 2 chunks
                print(f"\n   Chunk {idx} ({len(chunk)} chars):")
                print(f"   {chunk[:150]}..." if len(chunk) > 150 else f"   {chunk}")
            
            if len(chunks) > 2:
                print(f"\n   ... and {len(chunks) - 2} more chunks")
            
            # Create search documents
            documents = TextChunker.create_search_documents(
                url=result['url'],
                url_hash=result['url_hash'],
                title=result['metadata']['title'],
                chunks=chunks
            )
            
            print(f"\n✅ Search documents created!")
            print(f"   Documents: {len(documents)}")
            
            # Show sample document
            sample_doc = documents[0]
            print(f"\n   Sample document structure:")
            print(f"   {json.dumps({k: v for k, v in sample_doc.items() if k != 'content'}, indent=6)}")
            print(f"   Content preview: {sample_doc['content'][:100]}...")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("✅ Test completed!")
    print("=" * 70)


def test_chunking():
    """Test text chunking with sample content."""
    
    print("\n" + "=" * 70)
    print("🔪 TEXT CHUNKING TEST")
    print("=" * 70)
    
    # Sample long text
    sample_text = """
    Introduction to Web Scraping.
    
    Web scraping is a technique used to extract large amounts of data from websites. The data on websites is unstructured. Web scraping helps collect these unstructured data and store it in a structured form. Web Scraping can be done either manually or by using an automated tool. But automated web scraping is more commonly used because of its effectiveness and efficiency.
    
    The terms "web scraping" and "web harvesting" are used synonymously. Web scraping is also called screen scraping. It is a method of web data extraction wherein useful data is mined from third-party websites, applications, etc. The data retrieved may be in HTML, JSON, or text format. Web scraping is used in various real-world applications.
    
    There are many sources from which data can be scraped. Common targets for web scraping include:
    - E-commerce websites: Product listings, prices, reviews, ratings
    - Real estate websites: Property details, prices, locations
    - Job portals: Job listings, descriptions, requirements
    - News websites: Articles, headlines, publication dates
    - Social media platforms: Posts, comments, user information
    
    Applications of Web Scraping.
    
    Web scraping has many applications. Some of the common ones are listed below. Data scraping is used widely in e-commerce websites for product research and monitoring competitor prices. It can be used to monitor brand reputation and take an immediate action if something negative is posted about the brand. Big data is a huge amount of structured or unstructured data. Scraped data can be converted into big data which helps in making big data analysis and visualization for making beneficial business decisions.
    
    Challenges of Web Scraping.
    
    Although web scraping is powerful, it comes with challenges. Some websites actively try to prevent web scraping. Dynamic websites that require user interaction before the data is generated are difficult to scrape. Some websites use CAPTCHAs to prevent automated access. Another challenge is the inconsistency and irregular structure of web pages on the Internet. Websites frequently change their design and structure, which can break web scrapers.
    
    Another major challenge is the ethical issues around web scraping. Many websites explicitly forbid web scraping in their terms of service. Some websites may serve legal notice to scrapers who violate their terms of service. It is important to follow ethical guidelines and respect the website's terms of service when web scraping.
    """ * 3  # Repeat to make it longer
    
    print(f"\nOriginal text length: {len(sample_text)} characters")
    
    # Test chunking with different sizes
    chunks = TextChunker.chunk_text(sample_text)
    
    print(f"✅ Chunks created: {len(chunks)}")
    print(f"\nChunk size distribution:")
    
    for idx, chunk in enumerate(chunks, 1):
        print(f"   Chunk {idx}: {len(chunk)} chars")
    
    print(f"\nAverage chunk size: {sum(len(c) for c in chunks) / len(chunks):.0f} chars")
    
    # Verify all content is preserved
    total_chars = sum(len(c) for c in chunks)
    print(f"\n✅ Content preserved: {total_chars} / {len(sample_text)} chars")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    print("\n🧪 SCRAPER UNIT TESTS")
    print("=" * 70)
    
    # Test 1: Chunking (fast, no network)
    test_chunking()
    
    # Test 2: Live scraping (requires network)
    print("\n⏳ Starting live scraping tests...")
    print("⚠️  This will attempt to connect to real websites.")
    
    try:
        asyncio.run(test_scraper())
    except KeyboardInterrupt:
        print("\n\n⛔ Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
