"""
HSN Classifier — BM25 Retriever
Fast first-pass retrieval using BM25 keyword matching.
"""
import re
import math
from collections import Counter
from typing import Optional
from models import ChapterChunk
from config import BM25_TOP_K, CHAPTER_BOOST_FACTOR


class BM25Retriever:
    """Okapi BM25 retrieval engine over chapter chunks."""
    
    def __init__(self, chunks: list[dict], keyword_chapter_map: dict):
        self.chunks = [ChapterChunk(**c) for c in chunks]
        self.keyword_chapter_map = keyword_chapter_map
        
        # Tokenize all documents
        self.tokenized_docs = [self._tokenize(c.text + " " + c.title + " " + 
                                               " ".join(c.subheadings) + " " + c.heading)
                               for c in self.chunks]
        
        # BM25 parameters
        self.k1 = 1.5
        self.b = 0.75
        self.epsilon = 0.25
        
        # Compute IDF
        self.doc_count = len(self.tokenized_docs)
        self.avgdl = sum(len(d) for d in self.tokenized_docs) / max(self.doc_count, 1)
        self.doc_freqs = self._compute_doc_freqs()
        self.idf = self._compute_idf()
    
    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization: lowercase, split on non-alphanumeric."""
        text = text.lower()
        tokens = re.findall(r'[a-z0-9]+', text)
        return tokens
    
    def _compute_doc_freqs(self) -> Counter:
        """Count how many documents contain each term."""
        df = Counter()
        for doc in self.tokenized_docs:
            unique_terms = set(doc)
            for term in unique_terms:
                df[term] += 1
        return df
    
    def _compute_idf(self) -> dict[str, float]:
        """Compute IDF for each term."""
        idf = {}
        for term, freq in self.doc_freqs.items():
            idf[term] = math.log((self.doc_count - freq + 0.5) / (freq + 0.5) + 1)
        return idf
    
    def _score_document(self, query_tokens: list[str], doc_idx: int) -> float:
        """Compute BM25 score for a single document."""
        doc = self.tokenized_docs[doc_idx]
        doc_len = len(doc)
        term_freqs = Counter(doc)
        
        score = 0.0
        for term in query_tokens:
            if term not in self.idf:
                continue
            tf = term_freqs.get(term, 0)
            idf = self.idf[term]
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
            score += idf * numerator / denominator
        
        return score
    
    def route_chapters(self, query: str) -> list[str]:
        """Use keyword routing to find candidate chapter files."""
        query_lower = query.lower()
        matched_files = set()
        
        for keyword, files in self.keyword_chapter_map.items():
            # Check if any keyword appears in the query
            kw_parts = keyword.split()
            if any(part in query_lower for part in kw_parts if len(part) > 2):
                matched_files.update(files)
        
        return list(matched_files)
    
    def search(self, query: str, top_k: Optional[int] = None) -> list[tuple[ChapterChunk, float]]:
        """Search for most relevant chunks using BM25 + routing boost."""
        if top_k is None:
            top_k = BM25_TOP_K
        
        query_tokens = self._tokenize(query)
        
        # Get routing-boosted chapters
        routed_files = self.route_chapters(query)
        routed_chapters = set()
        for f in routed_files:
            m = re.search(r'chapter_(\d+)', f)
            if m:
                routed_chapters.add(int(m.group(1)))
        
        # Score all documents
        scored = []
        for idx in range(self.doc_count):
            score = self._score_document(query_tokens, idx)
            
            # Apply routing boost
            if self.chunks[idx].chapter in routed_chapters:
                score *= CHAPTER_BOOST_FACTOR
            
            # Small boost for heading chunks (more specific than notes)
            if self.chunks[idx].chunk_type == "heading":
                score *= 1.1
            
            scored.append((idx, score))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Return top-K
        results = []
        for idx, score in scored[:top_k]:
            if score > 0:
                results.append((self.chunks[idx], score))
        
        return results
    
    def get_chunk_by_heading(self, heading: str) -> Optional[ChapterChunk]:
        """Direct lookup of a heading chunk."""
        for chunk in self.chunks:
            if chunk.heading == heading:
                return chunk
        return None
    
    def get_chapter_notes(self, chapter_num: int) -> Optional[ChapterChunk]:
        """Get the notes chunk for a specific chapter."""
        for chunk in self.chunks:
            if chunk.chapter == chapter_num and chunk.chunk_type == "chapter_notes":
                return chunk
        return None
    
    def get_gir_text(self) -> str:
        """Get the GIR (General Interpretive Rules) text."""
        for chunk in self.chunks:
            if chunk.chapter == 0:
                return chunk.text
        # Fallback: read from file
        gir_path = self.chunks[0].source_file if self.chunks else ""
        return ""
