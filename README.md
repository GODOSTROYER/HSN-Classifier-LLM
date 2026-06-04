# NexusHSN-Classifier

> **A modular, microservice-based AI application for automated HSN code classification using RAG. Features plug-and-play support for cloud APIs, custom endpoints, and local agent providers.**

NexusHSN-Classifier leverages advanced AI and a Retrieval-Augmented Generation (RAG) pipeline to correctly classify products according to the Harmonized System (HS) Nomenclature and the General Rules of Interpretation (GRI).

## Features
- **AI-Powered Classification:** Uses advanced LLMs (like Gemma 4) to reason through complex product descriptions.
- **RAG Architecture:** Searches across 2,200+ HS heading chunks from 97 chapters using BM25 and LLM-reranking.
- **Microservice Design:** Clean, modular structure makes it easy to maintain and scale.
- **Agent Provider Pattern:** Switch seamlessly between OpenRouter, custom API endpoints, and local script agents via environment variables.
- **Real-Time UI:** Includes a premium, glassmorphism frontend that streams the agent's decision-making process in real time using SSE.

## Architecture Overview
The system is divided into several clear components:
1. **Frontend:** HTML/CSS/JS interface using Server-Sent Events (SSE) for real-time progress updates.
2. **Backend API:** FastAPI server handling requests, routing, and SSE streaming.
3. **Retrieval Pipeline:** `indexer.py` and `retriever.py` build and query a local BM25 index over the HS chapters.
4. **Agent Providers:** `providers/` package abstracts the LLM interactions. It supports OpenRouter out of the box, as well as custom webhooks and local agents.
5. **GRI Agent Workflow:** `classifier.py` and `reranker.py` use the configured agent to filter candidates and execute a 7-step GRI methodology.

## Folder Structure
```text
z:/dserve/hsn_classifier/
├── .env                  # Configuration variables
├── .env.example          # Template for environment variables
├── requirements.txt      # Python dependencies
├── start.bat             # Windows launcher script
├── README.md             # This file
├── backend/
│   ├── server.py         # FastAPI application entry point
│   ├── config.py         # Configuration loader (dotenv)
│   ├── classifier.py     # Main GRI classification workflow
│   ├── reranker.py       # LLM-based reranking logic
│   ├── retriever.py      # BM25 search logic
│   ├── indexer.py        # Chunking and caching logic
│   ├── models.py         # Pydantic models
│   └── providers/        # AI Agent Providers
│       ├── __init__.py
│       ├── base.py       # AgentProvider abstract base class
│       ├── factory.py    # Factory to get the correct provider
│       ├── openrouter.py # OpenRouter API implementation
│       ├── custom_api.py # Custom API implementation
│       └── local_agent.py# Local script execution implementation
├── frontend/
│   ├── index.html        # Main web UI
│   ├── style.css         # Styling (Glassmorphism)
│   └── app.js            # Client-side logic & SSE handling
└── data/                 # HS Chapter markdown files
```

## Tech Stack
- **Backend:** Python 3.10+, FastAPI, Uvicorn, HTTPX, Pydantic, python-dotenv
- **Frontend:** HTML5, Vanilla JS, CSS3
- **AI/RAG:** Okapi BM25 (Rank-BM25), OpenRouter API (Gemma 4 31B)

## Installation Steps
1. Navigate to the project directory:
   ```bash
   cd z:/dserve/hsn_classifier
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Environment Variable Setup
Copy the example environment file and configure it:
```bash
cp .env.example .env
```
Edit `.env` to include your API keys and configuration preferences.

## How to Run the Project
You can run the project using the provided batch script or via the command line.

**Option 1: Using the Batch Script (Windows)**
```bash
start.bat
```

**Option 2: Using the Command Line**
```bash
cd backend
python server.py
```
Then open your browser and navigate to `http://127.0.0.1:8899`.

## How to Switch Between Agent Providers
The application uses the `AGENT_PROVIDER` environment variable to determine which AI agent to use. Modify your `.env` file to switch providers:

### 1. OpenRouter (Cloud AI)
```env
AGENT_PROVIDER=openrouter
OPENROUTER_API_KEY=your_api_key_here
MODEL_ID=google/gemma-4-31b-it:free
```

### 2. Custom API Endpoint
```env
AGENT_PROVIDER=custom
CUSTOM_AGENT_API_URL=http://localhost:8000/api/agent
CUSTOM_AGENT_API_KEY=optional_api_key
```

### 3. Local Agent (Subprocess Script)
```env
AGENT_PROVIDER=local
LOCAL_AGENT_PATH=./agents/local-agent.py
```

## How to Add a New Provider
The application uses an Adapter/Provider pattern, making it extremely easy to add new agents.

1. **Create a new file** in `backend/providers/` (e.g., `openai_provider.py`).
2. **Implement the `AgentProvider` interface** from `base.py`:
   ```python
   from .base import AgentProvider

   class OpenAIProvider(AgentProvider):
       async def generate_response(self, system_prompt: str, user_prompt: str, ...) -> str:
           # Implementation here
           pass
           
       async def generate_streaming_response(self, system_prompt: str, user_prompt: str, ...) -> AsyncGenerator[str, None]:
           # Implementation here
           pass
   ```
3. **Register your provider** in `backend/providers/factory.py`:
   ```python
   elif provider_name == "openai":
       from .openai_provider import OpenAIProvider
       return OpenAIProvider()
   ```
4. **Update your `.env` file** to use the new provider: `AGENT_PROVIDER=openai`.

## API Usage Examples
You can bypass the frontend and interact directly with the FastAPI backend.

**Classify a Product:**
```bash
curl -X POST http://127.0.0.1:8899/classify \
  -H "Content-Type: application/json" \
  -d '{"product_description": "Live cattle for breeding purposes"}'
```
*Note: This endpoint returns a Server-Sent Events (SSE) stream.*

**Check Server Health:**
```bash
curl http://127.0.0.1:8899/health
```

## Contribution Guidelines
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes (`git commit -m 'Add amazing feature'`).
4. Push to the branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request.

Please ensure your code adheres to clean code principles and does not hardcode configuration variables.

## License
Made by **Arnav Bule**.

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
