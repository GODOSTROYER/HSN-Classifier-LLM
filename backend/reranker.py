"""
HSN Classifier — LLM-based Reranker
Uses Gemma 4 31B to rerank BM25 candidates for maximum precision.
"""
import json
from models import ChapterChunk, RerankedCandidate
from providers import get_provider
from config import RERANK_TOP_K


RERANK_SYSTEM_PROMPT = """You are an expert customs classification assistant specializing in the Harmonized System (HS) Nomenclature.

Your task: Given a product description and a list of HS heading candidates, score each candidate for relevance.

For each candidate, provide:
- score: 0-10 (10 = perfect match, 0 = irrelevant)
- reason: Brief explanation of why this heading is or isn't relevant

Also identify if any cross-chapter references should be examined.

RESPOND ONLY WITH VALID JSON in this exact format:
{
  "scores": [
    {"chunk_id": "...", "score": 8, "reason": "..."},
    ...
  ],
  "cross_refs": ["chapter_XX.md", ...],
  "top_heading": "XX.XX",
  "reasoning": "Brief explanation of your top pick"
}"""


async def rerank_candidates(product_description: str, 
                            candidates: list[tuple[ChapterChunk, float]],
                            top_k: int = None) -> list[RerankedCandidate]:
    """Use Gemma 4 to rerank BM25 candidates."""
    if top_k is None:
        top_k = RERANK_TOP_K
    
    # Build candidate summaries for the LLM
    candidate_summaries = []
    for i, (chunk, bm25_score) in enumerate(candidates):
        summary = {
            "chunk_id": chunk.chunk_id,
            "heading": chunk.heading or "N/A",
            "chapter": chunk.chapter,
            "title": chunk.title[:200],
            "type": chunk.chunk_type,
            "subheadings": chunk.subheadings[:10],
            "text_preview": chunk.text[:500]
        }
        candidate_summaries.append(summary)
    
    user_prompt = f"""PRODUCT TO CLASSIFY: "{product_description}"

CANDIDATE HS HEADINGS (ranked by keyword relevance):

{json.dumps(candidate_summaries, indent=2, ensure_ascii=False)}

Score each candidate 0-10 for relevance to the product. Focus on:
1. Does the heading text actually describe this product?
2. Do the subheadings contain a specific match?
3. Would this product be classified here per GRI rules?

Return JSON only."""

    try:
        provider = get_provider()
        response_text = await provider.generate_response(RERANK_SYSTEM_PROMPT, user_prompt, 
                                          max_tokens=4096, temperature=0.1)
        
        # Parse JSON from response (handle markdown code blocks)
        json_text = response_text
        if "```json" in json_text:
            json_text = json_text.split("```json")[1].split("```")[0]
        elif "```" in json_text:
            json_text = json_text.split("```")[1].split("```")[0]
        
        result = json.loads(json_text.strip())
        scores_map = {s["chunk_id"]: s for s in result.get("scores", [])}
        
    except Exception as e:
        print(f"[Reranker] LLM call failed: {e}, falling back to BM25 order")
        scores_map = {}
    
    # Build reranked list
    reranked = []
    for chunk, bm25_score in candidates:
        llm_score_data = scores_map.get(chunk.chunk_id, {})
        rerank_score = float(llm_score_data.get("score", 0))
        
        # Combined score: weighted average of BM25 (normalized) and LLM score
        max_bm25 = max(s for _, s in candidates) if candidates else 1
        norm_bm25 = bm25_score / max_bm25 if max_bm25 > 0 else 0
        combined = 0.3 * norm_bm25 * 10 + 0.7 * rerank_score
        
        reranked.append(RerankedCandidate(
            chunk=chunk,
            bm25_score=bm25_score,
            rerank_score=rerank_score,
            combined_score=combined
        ))
    
    # Sort by combined score
    reranked.sort(key=lambda x: x.combined_score, reverse=True)
    
    return reranked[:top_k]
