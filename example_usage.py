"""
Example usage and testing script for the scraper function.
Run after: func start (in another terminal)
"""
import json
import requests
import asyncio
from pathlib import Path

# Local development endpoint
BASE_URL = "http://localhost:7071/api"


def test_health_check():
    """Test the health check endpoint."""
    print("\n🏥 Health Check:")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")


def test_scrape_simple_site():
    """Test scraping a simple static website."""
    print("\n📄 Testing Simple Site (Wikipedia):")
    
    url = "https://en.wikipedia.org/wiki/Web_scraping"
    
    payload = {
        "url": url,
        "upload_to_blob": False  # Set to True if you have Azure Storage configured
    }
    
    print(f"Request: POST {BASE_URL}/scrape-url")
    print(f"URL: {url}")
    
    response = requests.post(
        f"{BASE_URL}/scrape-url",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response:\n{json.dumps(result, indent=2)}")
    
    if response.status_code == 200 and result.get("status") == "success":
        print(f"\n✅ SUCCESS")
        print(f"   Documents created: {result.get('documents_created')}")
        print(f"   Content length: {result.get('content_length')} chars")
        print(f"   Chunks: {result.get('chunks')}")
    else:
        print(f"\n❌ FAILED")


def test_scrape_js_site():
    """Test scraping a JavaScript-heavy website."""
    print("\n⚙️ Testing JavaScript Site:")
    
    url = "https://example.com"  # Simple site for testing
    
    payload = {
        "url": url,
        "upload_to_blob": False
    }
    
    print(f"Request: POST {BASE_URL}/scrape-url")
    print(f"URL: {url}")
    
    response = requests.post(
        f"{BASE_URL}/scrape-url",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response:\n{json.dumps(result, indent=2)}")
    
    if response.status_code == 200 and result.get("status") == "success":
        print(f"\n✅ SUCCESS")
    else:
        print(f"\n❌ FAILED")


def test_invalid_url():
    """Test error handling with invalid URL."""
    print("\n❌ Testing Invalid URL:")
    
    payload = {
        "url": "not-a-valid-url",
        "upload_to_blob": False
    }
    
    print(f"Request: POST {BASE_URL}/scrape-url")
    print(f"URL: not-a-valid-url")
    
    response = requests.post(
        f"{BASE_URL}/scrape-url",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response:\n{json.dumps(result, indent=2)}")
    
    if response.status_code >= 400:
        print(f"\n✅ Error handled correctly")


def test_missing_url_parameter():
    """Test error handling with missing URL parameter."""
    print("\n❌ Testing Missing URL Parameter:")
    
    payload = {
        "upload_to_blob": False
    }
    
    print(f"Request: POST {BASE_URL}/scrape-url (no URL)")
    
    response = requests.post(
        f"{BASE_URL}/scrape-url",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response:\n{json.dumps(result, indent=2)}")
    
    if response.status_code == 400:
        print(f"\n✅ Error handled correctly")


def test_blob_storage_upload():
    """Test with blob storage upload (requires Azure Storage configured)."""
    print("\n☁️ Testing Blob Storage Upload:")
    print("⚠️  Requires Azure Storage connection string in local.settings.json")
    
    url = "https://docs.microsoft.com/en-us/azure/"
    
    payload = {
        "url": url,
        "upload_to_blob": True  # Enable blob upload
    }
    
    print(f"Request: POST {BASE_URL}/scrape-url (with blob upload)")
    print(f"URL: {url}")
    
    response = requests.post(
        f"{BASE_URL}/scrape-url",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response:\n{json.dumps(result, indent=2)}")
    
    if response.status_code == 200:
        if result.get("blob_name"):
            print(f"\n✅ Blob stored at: {result['blob_name']}")
        elif result.get("blob_upload_error"):
            print(f"\n⚠️ Upload error: {result['blob_upload_error']}")


def main():
    """Run all tests."""
    print("=" * 70)
    print("🚀 Azure Function Scraper - Test Suite")
    print("=" * 70)
    print("\n📋 Prerequisites:")
    print("   1. Start the function: func start")
    print("   2. Install test dependencies: pip install requests")
    print("   3. Run this script: python example_usage.py")
    
    try:
        # Test connectivity
        print("\n⏳ Checking function availability...")
        test_health_check()
        
        # Run tests
        test_missing_url_parameter()
        test_invalid_url()
        test_scrape_simple_site()
        test_scrape_js_site()
        # test_blob_storage_upload()  # Uncomment if you have storage configured
        
        print("\n" + "=" * 70)
        print("✅ Test suite complete!")
        print("=" * 70)
    
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to function")
        print("   Make sure to run: func start")
        print("   in another terminal before running this script")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")


if __name__ == "__main__":
    main()
