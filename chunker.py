"""
Intelligent text chunking for Azure AI Search optimization.
Chunks content by sentences/paragraphs to maintain semantic coherence.
"""
import re
from typing import List
from logger import StructuredLogger

logger = StructuredLogger(__name__)


class TextChunker:
    """Chunks text intelligently for AI Search indexing."""
    
    # Approximate tokens per chunk (AI Search ~2000 char limit per field)
    TARGET_CHUNK_SIZE = 1500  # characters
    MIN_CHUNK_SIZE = 200      # minimum meaningful chunk
    MAX_CHUNK_SIZE = 2500     # maximum per field
    
    @staticmethod
    def _tokenize_sentences(text: str) -> List[str]:
        """Split text into sentences."""
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    @staticmethod
    def _tokenize_paragraphs(text: str) -> List[str]:
        """Split text into paragraphs."""
        paragraphs = text.split('\n\n')
        return [p.strip() for p in paragraphs if p.strip()]
    
    @classmethod
    def chunk_text(
        cls,
        text: str,
        target_size: int = TARGET_CHUNK_SIZE
    ) -> List[str]:
        """
        Intelligently chunk text for AI Search.
        Prefers to keep paragraphs and sentences together.
        
        Args:
            text: The text to chunk
            target_size: Target chunk size in characters
        
        Returns:
            List of text chunks
        """
        if len(text) <= target_size:
            return [text]
        
        chunks = []
        paragraphs = cls._tokenize_paragraphs(text)
        
        current_chunk = ""
        
        for paragraph in paragraphs:
            # If a single paragraph is too large, split by sentences
            if len(paragraph) > target_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                
                # Split paragraph into sentences
                sentences = cls._tokenize_sentences(paragraph)
                sentence_chunk = ""
                
                for sentence in sentences:
                    test_chunk = (sentence_chunk + " " + sentence).strip()
                    
                    if len(test_chunk) <= target_size:
                        sentence_chunk = test_chunk
                    else:
                        if sentence_chunk and len(sentence_chunk) >= cls.MIN_CHUNK_SIZE:
                            chunks.append(sentence_chunk)
                        sentence_chunk = sentence
                
                if sentence_chunk and len(sentence_chunk) >= cls.MIN_CHUNK_SIZE:
                    chunks.append(sentence_chunk)
            else:
                # Try to add paragraph to current chunk
                test_chunk = (current_chunk + "\n\n" + paragraph).strip()
                
                if len(test_chunk) <= target_size:
                    current_chunk = test_chunk
                else:
                    if current_chunk and len(current_chunk) >= cls.MIN_CHUNK_SIZE:
                        chunks.append(current_chunk)
                    current_chunk = paragraph
        
        # Add remaining chunk
        if current_chunk and len(current_chunk) >= cls.MIN_CHUNK_SIZE:
            chunks.append(current_chunk)
        
        # Validate chunks are within limits
        valid_chunks = []
        for chunk in chunks:
            if cls.MIN_CHUNK_SIZE <= len(chunk) <= cls.MAX_CHUNK_SIZE:
                valid_chunks.append(chunk)
        
        logger.info("Text chunking complete", {
            "original_size": len(text),
            "chunk_count": len(valid_chunks),
            "avg_chunk_size": int(len(text) / len(valid_chunks)) if valid_chunks else 0
        })
        
        return valid_chunks if valid_chunks else chunks
    
    @staticmethod
    def create_search_documents(
        url: str,
        url_hash: str,
        title: str,
        chunks: List[str]
    ) -> List[dict]:
        """
        Create Azure AI Search compatible documents from chunks.
        
        Args:
            url: Source URL
            url_hash: Hash identifier for URL
            title: Document title
            chunks: List of text chunks
        
        Returns:
            List of document dicts ready for AI Search indexing
        """
        documents = []
        
        for idx, chunk in enumerate(chunks, 1):
            doc_id = f"{url_hash}_chunk_{idx:03d}"
            
            documents.append({
                "id": doc_id,
                "source_url": url,
                "url_hash": url_hash,
                "title": title,
                "chunk_number": idx,
                "total_chunks": len(chunks),
                "content": chunk,
            })
        
        logger.info("Search documents created", {
            "url_hash": url_hash,
            "document_count": len(documents)
        })
        
        return documents
