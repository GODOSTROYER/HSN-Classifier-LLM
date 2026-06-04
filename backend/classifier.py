"""
HSN Classifier — Main Classification Agent
Implements the full GRI-compliant classification workflow.
"""
import json
import asyncio
from pathlib import Path
from typing import AsyncGenerator, Callable, Optional
from models import (ChapterChunk, ClassificationResult, GRIStep, 
                    WorkflowStep, StepStatus, RerankedCandidate)
from retriever import BM25Retriever
from reranker import rerank_candidates
from providers import get_provider
from config import DATA_DIR, CHAPTERS_DIR, FINAL_CONTEXT_CHUNKS


# ─── Classification System Prompt ─────────────────────────────────────────────

CLASSIFICATION_SYSTEM_PROMPT = """You are an expert Indian Customs classification consultant with deep knowledge of the Harmonized System (HS) Nomenclature, WCO Explanatory Notes, and Indian Customs Tariff Act (CTA 1975).

## YOUR METHODOLOGY — General Rules of Interpretation (GRI)

Apply GRI sequentially. STOP as soon as classification is resolved:

### GRI 1 (Primary Rule — resolves ~90% of cases)
- Read the heading text and any relevant Section/Chapter Notes
- The heading text and Notes have LEGAL FORCE
- Explanatory Notes are guidance only (but highly persuasive)
- If ONE heading clearly covers the product → CLASSIFIED → STOP

### GRI 2(a) — Incomplete/Unfinished Goods
- Applies if the product is incomplete, unfinished, unassembled, or disassembled
- Classify as if complete/finished, provided it has the essential character

### GRI 2(b) — Mixtures and Combinations
- Extends each heading to include mixtures/combinations with other materials
- May create prima facie classifiability under 2+ headings → proceed to GRI 3

### GRI 3 — When 2+ Headings Apply
- (a) Most specific description wins
- (b) Essential character of mixture/composite/set
- (c) Last in numerical order (tiebreaker)

### GRI 4 — Most Akin (Rare)
- Classify by analogy to most similar goods

### GRI 5 — Packing
- (a) Specially shaped containers classified with contents
- (b) Packing materials classified with contents (unless clearly reusable)

### GRI 6 — Subheading Classification  
- Apply GRI 1-5 mutatis mutandis at the subheading level
- Compare ONLY within the same heading at the same dash level

## OUTPUT FORMAT

You MUST respond with valid JSON in this exact structure:
{
  "hsn_code": "XXXX.XX.XX",
  "hsn_description": "Full description from the tariff",
  "confidence": 0.0-1.0,
  "confidence_label": "HIGH|MEDIUM|LOW",
  "chapter": "XX",
  "section": "Roman numeral",
  "gri_steps": [
    {
      "rule": "GRI 1",
      "applied": true,
      "reasoning": "Detailed reasoning with verbatim quotes...",
      "headings_remaining": ["XX.XX"],
      "resolved": true
    }
  ],
  "subheadings_considered": ["XXXX.XX", "XXXX.XX"],
  "verbatim_quotes": ["Exact quote from the explanatory notes..."],
  "cross_references": ["Heading XX.XX - reason"],
  "reasoning_summary": "Complete classification reasoning...",
  "alternative_codes": [
    {"code": "XXXX.XX", "reason": "Why this was considered but rejected"}
  ],
  "classification_opinion": "Full formal Classification Opinion text"
}

## CRITICAL RULES
1. ALWAYS quote verbatim from the provided chapter text — never paraphrase legal text
2. Work through GRI sequentially — do NOT skip to GRI 3 without establishing GRI 1 fails
3. Check Chapter Notes and Section Notes BEFORE heading text
4. If confidence < 0.7, flag as requiring manual review
5. Consider exclusion notes — products explicitly excluded from a heading
6. For subheading determination (GRI 6), compare only at same dash level"""


# ─── Workflow Steps ────────────────────────────────────────────────────────────

WORKFLOW_STEPS = [
    WorkflowStep(step=1, name="Keyword Routing", detail="Matching product to candidate chapters"),
    WorkflowStep(step=2, name="BM25 Retrieval", detail="Searching across all HS headings"),
    WorkflowStep(step=3, name="LLM Reranking", detail="AI scoring candidate relevance"),
    WorkflowStep(step=4, name="Context Assembly", detail="Loading GIR + chapter notes + headings"),
    WorkflowStep(step=5, name="GRI Classification", detail="Applying GRI 1-6 methodology"),
    WorkflowStep(step=6, name="Confidence Scoring", detail="Validating and scoring result"),
    WorkflowStep(step=7, name="Output Generation", detail="Formatting Classification Opinion"),
]


class HSNClassifier:
    """Main classification agent implementing the full GRI workflow."""
    
    def __init__(self, index: dict):
        self.index = index
        self.retriever = BM25Retriever(
            index["chunks"], 
            index.get("keyword_chapter_map", {})
        )
        self.gir_text = self._load_gir()
    
    def _load_gir(self) -> str:
        """Load General Interpretive Rules text."""
        gir_path = DATA_DIR / "chapters" / "chapter_00_GIR.md"
        if gir_path.exists():
            text = gir_path.read_text(encoding='utf-8')
            # Take first 8000 chars (rules without section notes)
            return text[:8000]
        return ""
    
    def _load_chapter_full(self, chapter_num: int) -> str:
        """Load full chapter text for deep analysis."""
        # Try part files first for large chapters
        if chapter_num in (84, 85, 90):
            parts = sorted(CHAPTERS_DIR.glob(f"chapter_{chapter_num:02d}_part*.md"))
            if parts:
                # Return first part as it contains notes + beginning headings
                return parts[0].read_text(encoding='utf-8')[:20000]
        
        path = CHAPTERS_DIR / f"chapter_{chapter_num:02d}.md"
        if path.exists():
            text = path.read_text(encoding='utf-8')
            return text[:20000]  # Cap for context budget
        return ""
    
    async def classify(self, product_description: str,
                        on_progress: Optional[Callable] = None) -> ClassificationResult:
        """Run the full classification workflow."""
        
        result = ClassificationResult(product_description=product_description)
        
        async def emit(step_num: int, status: str, detail: str = "", 
                       data: dict = None, progress: float = 0):
            if on_progress:
                await on_progress({
                    "step": step_num,
                    "name": WORKFLOW_STEPS[step_num - 1].name if step_num <= len(WORKFLOW_STEPS) else "",
                    "status": status,
                    "detail": detail,
                    "progress_pct": progress,
                    "data": data or {}
                })
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 1: Keyword Routing
        # ═══════════════════════════════════════════════════════════════════════
        await emit(1, "running", "Scanning chapter_routing.md for keyword matches...")
        
        routed_chapters = self.retriever.route_chapters(product_description)
        routed_nums = []
        for f in routed_chapters:
            import re
            m = re.search(r'chapter_(\d+)', f)
            if m:
                routed_nums.append(int(m.group(1)))
        
        await emit(1, "done", 
                   f"Found {len(routed_chapters)} candidate chapters: {routed_nums[:8]}",
                   {"routed_chapters": routed_nums[:8]}, 14)
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 2: BM25 Retrieval
        # ═══════════════════════════════════════════════════════════════════════
        await emit(2, "running", f"BM25 searching across {len(self.index['chunks'])} indexed chunks...")
        
        bm25_results = self.retriever.search(product_description, top_k=40)
        
        top_bm25 = [
            {"heading": c.heading, "chapter": c.chapter, 
             "title": c.title[:80], "score": round(s, 2)}
            for c, s in bm25_results[:10]
        ]
        
        await emit(2, "done",
                   f"Retrieved {len(bm25_results)} candidates, top: {bm25_results[0][0].heading if bm25_results else 'none'}",
                   {"top_candidates": top_bm25}, 28)
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 3: LLM Reranking
        # ═══════════════════════════════════════════════════════════════════════
        await emit(3, "running", "Sending candidates to Gemma 4 for relevance scoring...")
        
        # Take top 25 for reranking (balance between coverage and token budget)
        reranked = await rerank_candidates(product_description, bm25_results[:25])
        
        top_reranked = [
            {"heading": r.chunk.heading, "chapter": r.chunk.chapter,
             "title": r.chunk.title[:80], "bm25": round(r.bm25_score, 2),
             "llm_score": r.rerank_score, "combined": round(r.combined_score, 2)}
            for r in reranked[:8]
        ]
        
        await emit(3, "done",
                   f"Reranked — top heading: {reranked[0].chunk.heading if reranked else 'none'} "
                   f"(score: {reranked[0].combined_score:.1f}/10)" if reranked else "No candidates",
                   {"reranked": top_reranked}, 42)
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 4: Context Assembly
        # ═══════════════════════════════════════════════════════════════════════
        await emit(4, "running", "Loading GIR rules + chapter notes + heading details...")
        
        # Assemble context from top reranked chunks
        context_parts = []
        
        # 1. GIR (always included — critical for methodology)
        context_parts.append(f"=== GENERAL INTERPRETIVE RULES (GIR) ===\n{self.gir_text}\n")
        
        # 2. Chapter notes for top chapters
        seen_chapters = set()
        for r in reranked[:FINAL_CONTEXT_CHUNKS]:
            ch = r.chunk.chapter
            if ch not in seen_chapters and r.chunk.notes:
                context_parts.append(
                    f"=== CHAPTER {ch} NOTES ===\n{r.chunk.notes}\n"
                )
                seen_chapters.add(ch)
        
        # 3. Top heading chunks (full text)
        for r in reranked[:FINAL_CONTEXT_CHUNKS]:
            context_parts.append(
                f"=== HEADING {r.chunk.heading} (Chapter {r.chunk.chapter}) ===\n"
                f"Title: {r.chunk.title}\n"
                f"Subheadings: {', '.join(r.chunk.subheadings[:15])}\n"
                f"Source: {r.chunk.source_file}\n\n"
                f"{r.chunk.text}\n"
            )
        
        full_context = "\n\n".join(context_parts)
        context_chars = len(full_context)
        
        await emit(4, "done",
                   f"Assembled {context_chars:,} chars of context "
                   f"({len(seen_chapters)} chapters, {min(len(reranked), FINAL_CONTEXT_CHUNKS)} headings, GIR)",
                   {"context_chars": context_chars, 
                    "chapters_loaded": list(seen_chapters),
                    "headings_loaded": [r.chunk.heading for r in reranked[:FINAL_CONTEXT_CHUNKS]]},
                   56)
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 5: GRI Classification (Main LLM Call)
        # ═══════════════════════════════════════════════════════════════════════
        await emit(5, "running", "Gemma 4 applying GRI 1-6 methodology — this may take 30-60 seconds...")
        
        classification_prompt = f"""PRODUCT TO CLASSIFY:
"{product_description}"

RETRIEVED HS CONTEXT (ranked by relevance):

{full_context}

---

Now classify this product following GRI methodology strictly.
- Start with GRI 1 — check heading texts and Chapter/Section Notes
- Only proceed to GRI 2+ if GRI 1 doesn't resolve
- Quote verbatim from the context above
- Determine the most specific HSN code possible (6-8 digits)
- Assess your confidence honestly

Respond with the JSON format specified in your system prompt."""
        
        try:
            provider = get_provider()
            llm_response = await provider.generate_response(
                CLASSIFICATION_SYSTEM_PROMPT,
                classification_prompt,
                max_tokens=8192,
                temperature=0.15
            )
            
            # Parse JSON from response
            json_text = llm_response
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0]
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0]
            
            classification_data = json.loads(json_text.strip())
            
            # Populate result
            result.hsn_code = classification_data.get("hsn_code", "")
            result.hsn_description = classification_data.get("hsn_description", "")
            result.confidence = float(classification_data.get("confidence", 0))
            result.confidence_label = classification_data.get("confidence_label", "LOW")
            result.chapter = classification_data.get("chapter", "")
            result.section = classification_data.get("section", "")
            result.subheadings_considered = classification_data.get("subheadings_considered", [])
            result.verbatim_quotes = classification_data.get("verbatim_quotes", [])
            result.cross_references = classification_data.get("cross_references", [])
            result.reasoning_summary = classification_data.get("reasoning_summary", "")
            result.alternative_codes = classification_data.get("alternative_codes", [])
            result.classification_opinion = classification_data.get("classification_opinion", "")
            
            # Parse GRI steps
            for gs in classification_data.get("gri_steps", []):
                result.gri_steps.append(GRIStep(
                    rule=gs.get("rule", ""),
                    applied=gs.get("applied", False),
                    reasoning=gs.get("reasoning", ""),
                    headings_remaining=gs.get("headings_remaining", []),
                    resolved=gs.get("resolved", False)
                ))
            
            await emit(5, "done",
                       f"Classification complete — HSN: {result.hsn_code} "
                       f"(Confidence: {result.confidence_label})",
                       {"hsn_code": result.hsn_code,
                        "confidence": result.confidence,
                        "gri_steps_count": len(result.gri_steps)},
                       78)
            
        except json.JSONDecodeError as e:
            await emit(5, "error", f"Failed to parse LLM JSON: {e}")
            result.reasoning_summary = f"LLM response parsing error: {e}\nRaw: {llm_response[:500]}"
            result.confidence = 0.1
            result.confidence_label = "LOW"
        except Exception as e:
            await emit(5, "error", f"LLM call failed: {e}")
            result.reasoning_summary = f"LLM error: {e}"
            result.confidence = 0.0
            result.confidence_label = "ERROR"
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 6: Confidence Scoring & Validation
        # ═══════════════════════════════════════════════════════════════════════
        await emit(6, "running", "Validating classification and calibrating confidence...")
        
        # Validate HSN code format
        import re
        hsn_valid = bool(re.match(r'^\d{4}(\.\d{2}){0,2}$', result.hsn_code))
        
        # Adjust confidence based on validation checks
        validation_notes = []
        if not hsn_valid and result.hsn_code:
            # Try to fix common format issues
            clean = re.sub(r'[^0-9.]', '', result.hsn_code)
            if re.match(r'^\d{4}(\.\d{2}){0,2}$', clean):
                result.hsn_code = clean
                hsn_valid = True
            else:
                validation_notes.append("HSN code format invalid")
                result.confidence *= 0.7
        
        if not result.verbatim_quotes:
            validation_notes.append("No verbatim quotes provided")
            result.confidence *= 0.85
        
        if not result.gri_steps:
            validation_notes.append("No GRI steps documented")
            result.confidence *= 0.8
        
        # Recalculate confidence label
        if result.confidence >= 0.8:
            result.confidence_label = "HIGH"
        elif result.confidence >= 0.5:
            result.confidence_label = "MEDIUM"
        else:
            result.confidence_label = "LOW"
        
        await emit(6, "done",
                   f"Confidence: {result.confidence:.0%} ({result.confidence_label})"
                   + (f" — Issues: {', '.join(validation_notes)}" if validation_notes else " — All checks passed"),
                   {"confidence": result.confidence,
                    "confidence_label": result.confidence_label,
                    "validation_notes": validation_notes,
                    "hsn_valid": hsn_valid},
                   92)
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 7: Output Generation
        # ═══════════════════════════════════════════════════════════════════════
        await emit(7, "running", "Formatting final Classification Opinion...")
        
        # Build formal opinion if not provided by LLM
        if not result.classification_opinion:
            result.classification_opinion = self._format_opinion(result)
        
        await emit(7, "done", "Classification complete!",
                   {"result": result.model_dump()}, 100)
        
        return result
    
    def _format_opinion(self, result: ClassificationResult) -> str:
        """Format a formal Classification Opinion."""
        gri_text = ""
        for gs in result.gri_steps:
            status = "✅ RESOLVED" if gs.resolved else ("✓ Applied" if gs.applied else "— Skipped")
            gri_text += f"\n{gs.rule}: {status}\n  {gs.reasoning}\n"
        
        return f"""═══ CLASSIFICATION OPINION ═══

A. PRODUCT: {result.product_description}

B. PROPOSED HSN CODE: {result.hsn_code}
   Description: {result.hsn_description}

C. CHAPTER: {result.chapter} | SECTION: {result.section}

D. GRI APPLICATION:
{gri_text}

E. CONFIDENCE: {result.confidence:.0%} ({result.confidence_label})

F. SUBHEADINGS CONSIDERED: {', '.join(result.subheadings_considered)}

G. VERBATIM REFERENCES:
{chr(10).join('  • ' + q for q in result.verbatim_quotes)}

H. ALTERNATIVES CONSIDERED:
{chr(10).join('  • ' + a.get('code','') + ' — ' + a.get('reason','') for a in result.alternative_codes)}

I. REASONING:
{result.reasoning_summary}

═══ END OF OPINION ═══"""
