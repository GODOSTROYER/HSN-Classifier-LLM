"""
HSN Classifier — Chapter Indexer
Parses all chapter markdown files into searchable chunks.
"""
import re
import json
import hashlib
from pathlib import Path
from typing import Optional
from models import ChapterChunk, RoutingEntry
from config import DATA_DIR, CHAPTERS_DIR, INDEX_CACHE


def parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from markdown."""
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if not match:
        return {}
    meta = {}
    for line in match.group(1).split('\n'):
        if ':' in line:
            key, val = line.split(':', 1)
            val = val.strip().strip("'\"")
            meta[key.strip()] = val
    return meta


def extract_chapter_notes(text: str) -> str:
    """Extract the Notes section at the beginning of a chapter."""
    # Notes appear after the chapter title, before the ### GENERAL section
    notes_parts = []
    in_notes = False
    for line in text.split('\n'):
        if re.match(r'\*\*Notes?\.\*\*', line):
            in_notes = True
        if in_notes:
            if line.startswith('### GENERAL') or line.startswith('### ') or re.match(r'^\d{2}\.\d{2}$', line.strip()):
                break
            notes_parts.append(line)
    return '\n'.join(notes_parts).strip()


def split_into_headings(text: str, chapter_num: int, source_file: str, 
                         chapter_title: str, section: str) -> list[ChapterChunk]:
    """Split chapter text into heading-level chunks."""
    chunks = []
    
    # Remove frontmatter
    text_body = re.sub(r'^---\s*\n.*?\n---\s*\n', '', text, flags=re.DOTALL)
    
    # Extract chapter notes
    chapter_notes = extract_chapter_notes(text_body)
    
    # If chapter notes exist, create a notes chunk
    if chapter_notes and len(chapter_notes) > 50:
        notes_chunk = ChapterChunk(
            chunk_id=f"ch{chapter_num:02d}_notes",
            chapter=chapter_num,
            heading="",
            title=f"Chapter {chapter_num} Notes",
            section=section,
            chapter_title=chapter_title,
            text=chapter_notes,
            chunk_type="chapter_notes",
            source_file=source_file,
            notes=chapter_notes
        )
        chunks.append(notes_chunk)
    
    # Find the GENERAL section
    general_match = re.search(r'### GENERAL\s*\n(.*?)(?=\n\d{2}\.\d{2}\s*$|\n\*\*\d{2}\.\d{2})', 
                               text_body, re.DOTALL | re.MULTILINE)
    if general_match:
        general_text = general_match.group(1).strip()
        if len(general_text) > 50:
            gen_chunk = ChapterChunk(
                chunk_id=f"ch{chapter_num:02d}_general",
                chapter=chapter_num,
                heading="",
                title=f"Chapter {chapter_num} General",
                section=section,
                chapter_title=chapter_title,
                text=general_text[:8000],  # cap to avoid huge chunks
                chunk_type="general",
                source_file=source_file,
                notes=chapter_notes[:2000] if chapter_notes else ""
            )
            chunks.append(gen_chunk)
    
    # Split at heading boundaries: **XX.XX - Description**
    # Pattern: line starting with XX.XX (standalone heading number)
    heading_pattern = re.compile(
        r'^(\d{2}\.\d{2})\s*$',
        re.MULTILINE
    )
    
    heading_positions = [(m.start(), m.group(1)) for m in heading_pattern.finditer(text_body)]
    
    for i, (pos, heading_num) in enumerate(heading_positions):
        # Get text until next heading or end
        if i + 1 < len(heading_positions):
            end_pos = heading_positions[i + 1][0]
        else:
            end_pos = len(text_body)
        
        heading_text = text_body[pos:end_pos].strip()
        
        # Extract heading description from bold line
        desc_match = re.search(r'\*\*\d{2}\.\d{2}\s*-\s*(.*?)(?:\(\+\))?\.\*\*', heading_text)
        heading_title = desc_match.group(1).strip() if desc_match else ""
        
        # Extract subheading codes
        subheading_pattern = re.compile(r'(\d{4}\.\d{2})\s*-')
        subheadings = subheading_pattern.findall(heading_text)
        
        # Cap chunk size to ~10K chars to stay within token budget
        if len(heading_text) > 12000:
            heading_text = heading_text[:12000] + "\n\n[... truncated for context window ...]"
        
        chunk = ChapterChunk(
            chunk_id=f"ch{chapter_num:02d}_h{heading_num.replace('.', '')}",
            chapter=chapter_num,
            heading=heading_num,
            title=heading_title,
            section=section,
            chapter_title=chapter_title,
            text=heading_text,
            subheadings=subheadings,
            chunk_type="heading",
            source_file=source_file,
            notes=chapter_notes[:2000] if chapter_notes else ""
        )
        chunks.append(chunk)
    
    # If no headings found (e.g., GIR, reserved chapters), create one big chunk
    if not heading_positions and len(text_body.strip()) > 100:
        chunks.append(ChapterChunk(
            chunk_id=f"ch{chapter_num:02d}_full",
            chapter=chapter_num,
            heading="",
            title=chapter_title,
            section=section,
            chapter_title=chapter_title,
            text=text_body[:15000],
            chunk_type="full",
            source_file=source_file,
            notes=chapter_notes[:2000] if chapter_notes else ""
        ))
    
    return chunks


def parse_chapter_routing() -> list[RoutingEntry]:
    """Parse chapter_routing.md into routing entries."""
    routing_file = DATA_DIR / "chapter_routing.md"
    if not routing_file.exists():
        return []
    
    text = routing_file.read_text(encoding='utf-8')
    entries = []
    
    # Parse keyword-to-chapter mapping tables
    # Format: | keywords | `chapter_file` |
    table_pattern = re.compile(
        r'\|\s*(.+?)\s*\|\s*`?(chapters/chapter_\d+[^`|]*\.md)`?\s*\|',
        re.MULTILINE
    )
    
    for match in table_pattern.finditer(text):
        keywords_str = match.group(1).strip()
        if keywords_str.startswith('---') or keywords_str.lower() == 'keywords':
            continue
        chapter_file = match.group(2).strip()
        keywords = [k.strip().lower() for k in keywords_str.split(',') if k.strip()]
        
        entries.append(RoutingEntry(
            keywords=keywords,
            chapter_file=chapter_file
        ))
    
    return entries


def parse_heading_index() -> dict[str, dict]:
    """Parse heading_index.md into a lookup dict."""
    index_file = DATA_DIR / "heading_index.md"
    if not index_file.exists():
        return {}
    
    text = index_file.read_text(encoding='utf-8')
    headings = {}
    
    # Format: | XX.XX | chapters/chapter_XX.md | Description |
    pattern = re.compile(
        r'\|\s*(\d{2}\.\d{2})\s*\|\s*(chapters/chapter_\d+.*?\.md)\s*\|\s*(.*?)\s*\|',
        re.MULTILINE
    )
    
    for match in pattern.finditer(text):
        heading_num = match.group(1)
        chapter_file = match.group(2).strip()
        description = match.group(3).strip()
        headings[heading_num] = {
            "chapter_file": chapter_file,
            "description": description
        }
    
    return headings


def build_full_index() -> dict:
    """Build the complete searchable index from all chapter files."""
    all_chunks: list[ChapterChunk] = []
    
    # Parse each chapter file
    chapter_files = sorted(CHAPTERS_DIR.glob("chapter_*.md"))
    
    for filepath in chapter_files:
        filename = filepath.name
        
        # Skip part files — we use the full chapter files
        if '_part' in filename:
            continue
        
        # Extract chapter number
        num_match = re.search(r'chapter_(\d+)', filename)
        if not num_match:
            continue
        
        chapter_num_str = num_match.group(1)
        if chapter_num_str == '00':
            chapter_num = 0  # GIR
        else:
            chapter_num = int(chapter_num_str)
        
        text = filepath.read_text(encoding='utf-8')
        meta = parse_frontmatter(text)
        
        chapter_title = meta.get('title', f'Chapter {chapter_num}')
        section = meta.get('section', '')
        if section == 'null' or section is None:
            section = ''
        
        chunks = split_into_headings(
            text, chapter_num, filename, chapter_title, str(section)
        )
        all_chunks.extend(chunks)
    
    # Parse routing entries
    routing = parse_chapter_routing()
    
    # Parse heading index
    heading_index = parse_heading_index()
    
    # Build keyword-to-chapters mapping for fast routing
    keyword_chapter_map = {}
    for entry in routing:
        for kw in entry.keywords:
            if kw not in keyword_chapter_map:
                keyword_chapter_map[kw] = []
            keyword_chapter_map[kw].append(entry.chapter_file)
    
    index = {
        "chunks": [c.model_dump() for c in all_chunks],
        "routing": [r.model_dump() for r in routing],
        "heading_index": heading_index,
        "keyword_chapter_map": keyword_chapter_map,
        "stats": {
            "total_chunks": len(all_chunks),
            "total_chapters": len(set(c.chapter for c in all_chunks)),
            "total_headings": len([c for c in all_chunks if c.chunk_type == "heading"]),
            "total_routing_entries": len(routing),
        }
    }
    
    return index


def get_or_build_index(force_rebuild: bool = False) -> dict:
    """Get cached index or build fresh."""
    if not force_rebuild and INDEX_CACHE.exists():
        try:
            with open(INDEX_CACHE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    
    print("[Indexer] Building index from chapter files...")
    index = build_full_index()
    
    # Cache to disk
    INDEX_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_CACHE, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False)
    
    print(f"[Indexer] Done — {index['stats']['total_chunks']} chunks, "
          f"{index['stats']['total_headings']} headings across "
          f"{index['stats']['total_chapters']} chapters")
    
    return index


if __name__ == "__main__":
    idx = get_or_build_index(force_rebuild=True)
    print(json.dumps(idx["stats"], indent=2))
    # Show sample chunk
    for c in idx["chunks"][:5]:
        print(f"  {c['chunk_id']:30s}  ch={c['chapter']:02d}  heading={c['heading']:8s}  "
              f"type={c['chunk_type']:15s}  text={len(c['text']):6d} chars")
