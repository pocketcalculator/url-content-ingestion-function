"""
Web scraper with content extraction and filtering.
Supports both JavaScript-heavy and static content sites.
"""
import asyncio
import hashlib
from datetime import datetime
from typing import Optional, Tuple
from urllib.parse import urlparse

import requests
import trafilatura
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from logger import StructuredLogger

logger = StructuredLogger(__name__)


class ContentScraper:
    """Scrapes and extracts clean content from URLs."""
    
    TIMEOUT_SECONDS = 30
    MAX_RETRIES = 2
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    @staticmethod
    def _generate_url_hash(url: str) -> str:
        """Generate a hash identifier for the URL."""
        return hashlib.md5(url.encode()).hexdigest()[:8]
    
    @staticmethod
    async def _fetch_with_playwright(url: str) -> Optional[str]:
        """
        Fetch HTML content using Playwright for JavaScript-heavy sites.
        Returns HTML content or None on failure.
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(user_agent=ContentScraper.USER_AGENT)
                
                try:
                    await page.goto(url, wait_until="networkidle", timeout=ContentScraper.TIMEOUT_SECONDS * 1000)
                    html = await page.content()
                    return html
                finally:
                    await page.close()
                    await browser.close()
        
        except Exception as e:
            logger.warning("Playwright fetch failed", {
                "url": url,
                "error": str(e),
                "step": "playwright_fetch"
            })
            return None
    
    @staticmethod
    def _fetch_with_requests(url: str) -> Optional[str]:
        """
        Fetch HTML content using requests for simple sites.
        Falls back if Playwright fails.
        """
        try:
            response = requests.get(
                url,
                headers={"User-Agent": ContentScraper.USER_AGENT},
                timeout=ContentScraper.TIMEOUT_SECONDS
            )
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.warning("Requests fetch failed", {
                "url": url,
                "error": str(e),
                "step": "requests_fetch"
            })
            return None
    
    @staticmethod
    def _extract_content(html: str, url: str) -> Optional[Tuple[str, dict]]:
        """
        Extract main content using trafilatura with fallback to BeautifulSoup.
        Returns (content, metadata) or (None, {}) on failure.
        """
        try:
            # Try trafilatura first - excellent at extracting main content
            try:
                extracted = trafilatura.extract(
                    html,
                    include_comments=False,
                    favor_precision=True
                )
                
                if extracted:
                    # Extract metadata
                    try:
                        metadata = trafilatura.metadata.extract_metadata(html)
                    except:
                        metadata = None
                    
                    title = _extract_title_from_metadata(metadata) if metadata else "Unknown"
                    
                    logger.info("Content extracted with trafilatura", {
                        "url": url,
                        "content_length": len(extracted)
                    })
                    
                    return extracted, {
                        "title": title or _extract_title_fallback(html),
                        "author": _extract_author_from_metadata(metadata) if metadata else None,
                        "date": _extract_date_from_metadata(metadata) if metadata else None,
                    }
            except TypeError:
                # Fallback if trafilatura API differs
                pass
            
            # Fallback to BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            content = _extract_with_beautifulsoup(soup)
            title = _extract_title_fallback(html)
            
            logger.info("Content extracted with BeautifulSoup fallback", {
                "url": url,
                "content_length": len(content) if content else 0
            })
            
            return content, {"title": title}
        
        except Exception as e:
            logger.error("Content extraction failed", {
                "url": url,
                "error": str(e)
            })
            return None, {}
    
    @staticmethod
    def _filter_content(content: str) -> str:
        """Remove noise: extra whitespace, etc."""
        # Replace multiple spaces/newlines with single
        lines = [line.strip() for line in content.split('\n')]
        lines = [line for line in lines if line]  # Remove empty lines
        return '\n\n'.join(lines)
    
    async def scrape(self, url: str) -> Optional[dict]:
        """
        Scrape URL and extract clean content.
        
        Args:
            url: The URL to scrape
        
        Returns:
            Dict with keys: url, url_hash, content, metadata, scraped_at
            or None if all retries failed
        """
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            logger.error("Invalid URL", {"url": url})
            return None
        
        url_hash = self._generate_url_hash(url)
        
        # Try Playwright first for JS-heavy sites
        logger.info("Starting scrape", {"url": url, "url_hash": url_hash})
        html = await self._fetch_with_playwright(url)
        
        # Fallback to requests
        if not html:
            logger.info("Trying requests fallback", {"url": url})
            html = self._fetch_with_requests(url)
        
        if not html:
            logger.error("All fetch methods failed", {
                "url": url,
                "url_hash": url_hash
            })
            return None
        
        # Extract and filter content
        content, metadata = self._extract_content(html, url)
        if not content:
            logger.error("Content extraction failed", {
                "url": url,
                "url_hash": url_hash
            })
            return None
        
        filtered_content = self._filter_content(content)
        
        logger.info("Scrape successful", {
            "url": url,
            "url_hash": url_hash,
            "content_length": len(filtered_content),
            "title": metadata.get("title", "Unknown")
        })
        
        return {
            "url": url,
            "url_hash": url_hash,
            "content": filtered_content,
            "metadata": {
                "title": metadata.get("title", "Unknown"),
                "author": metadata.get("author"),
                "date": metadata.get("date"),
            },
            "scraped_at": datetime.utcnow().isoformat()
        }


def _extract_title_fallback(html: str) -> str:
    """Extract title from HTML as fallback."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.string.strip()
        h1 = soup.find("h1")
        if h1:
            return h1.get_text().strip()
    except:
        pass
    return "Unknown"


def _extract_title_from_metadata(metadata) -> str:
    """Safely extract title from trafilatura metadata object."""
    if not metadata:
        return "Unknown"
    if hasattr(metadata, "title"):
        return metadata.title or "Unknown"
    if hasattr(metadata, "get"):
        return metadata.get("title", "Unknown")
    return "Unknown"


def _extract_author_from_metadata(metadata) -> str:
    """Safely extract author from trafilatura metadata object."""
    if not metadata:
        return None
    if hasattr(metadata, "author"):
        return metadata.author
    if hasattr(metadata, "get"):
        return metadata.get("author")
    return None


def _extract_date_from_metadata(metadata) -> str:
    """Safely extract date from trafilatura metadata object."""
    if not metadata:
        return None
    if hasattr(metadata, "date"):
        return metadata.date
    if hasattr(metadata, "get"):
        return metadata.get("date")
    return None


def _extract_with_beautifulsoup(soup: BeautifulSoup) -> str:
    """Extract main text content using BeautifulSoup."""
    # Remove script and style elements
    for script in soup(["script", "style", "nav", "footer", "noscript"]):
        script.decompose()
    
    # Get text
    text = soup.get_text()
    return text
