"""
HSN Classifier — FastAPI Server with SSE Streaming
"""
import json
import asyncio
import time
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import HOST, PORT, INDEX_CACHE
from models import ClassifyRequest
from indexer import get_or_build_index
from classifier import HSNClassifier


# ─── Global State ─────────────────────────────────────────────────────────────
classifier: HSNClassifier = None
index_data: dict = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the index and classifier on startup."""
    global classifier, index_data
    print("\n+------------------------------------------------------+")
    print("|     HSN Code Classifier -- Agentic Workflow v1.0     |")
    print("+------------------------------------------------------+\n")
    
    print("[Server] Building search index...")
    index_data = get_or_build_index()
    classifier = HSNClassifier(index_data)
    
    print(f"[Server] Index ready — {index_data['stats']['total_chunks']} chunks, "
          f"{index_data['stats']['total_headings']} headings")
    print(f"[Server] Starting on http://{HOST}:{PORT}\n")
    
    yield
    
    print("[Server] Shutting down...")


app = FastAPI(title="HSN Classifier", lifespan=lifespan)

# CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main UI."""
    index_path = FRONTEND_DIR / "index.html"
    return index_path.read_text(encoding='utf-8')


@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "ok",
        "index_loaded": classifier is not None,
        "stats": index_data["stats"] if index_data else {},
    }


@app.post("/classify")
async def classify(request: ClassifyRequest):
    """Start classification — returns SSE stream."""
    
    async def event_stream():
        events = []
        event_ready = asyncio.Event()
        
        async def on_progress(data: dict):
            events.append(data)
            event_ready.set()
        
        # Start classification in a task
        task = asyncio.create_task(
            classifier.classify(request.product_description, on_progress=on_progress)
        )
        
        # Send initial event
        yield f"data: {json.dumps({'step': 0, 'name': 'Initialization', 'status': 'done', 'detail': 'Workflow started', 'progress_pct': 0, 'data': {'product': request.product_description}})}\n\n"
        
        # Stream progress events
        sent_count = 0
        while not task.done() or sent_count < len(events):
            if sent_count < len(events):
                event = events[sent_count]
                yield f"data: {json.dumps(event, default=str)}\n\n"
                sent_count += 1
            else:
                event_ready.clear()
                try:
                    await asyncio.wait_for(event_ready.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    # Send heartbeat
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        
        # Send any remaining events
        while sent_count < len(events):
            event = events[sent_count]
            yield f"data: {json.dumps(event, default=str)}\n\n"
            sent_count += 1
        
        # Get result
        try:
            result = await task
            yield f"data: {json.dumps({'type': 'complete', 'result': result.model_dump()})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/rebuild-index")
async def rebuild_index():
    """Force rebuild the search index."""
    global classifier, index_data
    
    # Delete cache
    if INDEX_CACHE.exists():
        INDEX_CACHE.unlink()
    
    index_data = get_or_build_index(force_rebuild=True)
    classifier = HSNClassifier(index_data)
    
    return {"status": "ok", "stats": index_data["stats"]}


@app.get("/stats")
async def stats():
    """Return index statistics."""
    if not index_data:
        return {"error": "Index not loaded"}
    return index_data["stats"]


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info"
    )
