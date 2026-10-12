# DocPilot AI — Intelligent Software Documentation Platform

> **Automatically understand any software project and generate complete developer documentation, architecture diagrams, API documentation, onboarding guides, and technical reports.**

---

## 💡 What is DocPilot AI?

Think of **DocPilot AI** as an AI engineer that joins your software team.
Instead of asking a senior developer:
> *"How does authentication work?"* or *"Where is the payment service?"*

The developer uploads the project into DocPilot AI. Within seconds, the platform parses the entire repository using syntax-aware static analysis, builds an internal knowledge graph, and automatically produces documentation that would normally take weeks or months to create manually:
- 📖 **Comprehensive README.md**
- 🏛️ **System Architecture Guides & Runtime Topologies**
- 🔌 **REST API Reference Specifications & Explorer**
- 🚀 **Day-1 Developer Onboarding Guides**
- 📊 **Technical Architecture & Health Reports**
- 📈 **Interactive React Flow & Mermaid Diagrams (Architecture, Sequence, ER, Dependencies)**
- 🤖 **Repository-Aware Grounded AI Assistant (RAG with citations)**
- 🔄 **Continuous Synchronization & Incremental Change Tracking**

---

## ⚡ Architecture & Pipeline

DocPilot AI follows a multi-stage incremental static intelligence pipeline:

```
Repository Input (ZIP / Git URL)
  │
  ▼
1. Extract & Discover Files
  │
  ▼
2. Language & Framework Detection
  │
  ▼
3. Syntax-Aware AST Parsing (Python, JS, TS)
  │
  ▼
4. Understand Project Directory Structure
  │
  ▼
5. Analyze Internal & External Dependencies
  │
  ▼
6. Discover REST API Endpoints
  │
  ▼
7. Analyze Database Models & Schemas
  │
  ▼
8. Build Internal Knowledge Graph
  │
  ▼
9. Synthesize Documentation (README, Arch, API, Onboarding)
  │
  ▼
10. Generate Diagrams (Mermaid & React Flow)
  │
  ▼
11. Build Vector Database & Enable AI Assistant
```

---

## 🛠️ Tech Stack

### Frontend
- **React 18** with **TypeScript**
- **Tailwind CSS** with modern dark-mode aesthetic
- **React Router v6**
- **@xyflow/react (React Flow)** for interactive module dependency and architecture graphs
- **Mermaid.js** for animated sequence and ER diagrams
- **Lucide React** for modern icons

### Backend
- **Python 3.12** & **FastAPI**
- **SQLAlchemy 2.0 (async)** with **SQLite / PostgreSQL**
- **Pydantic v2** for schemas and configuration
- **NetworkX** for directed knowledge graphs and dependency cycles
- **GitPython** for automated repository cloning and diff tracking
- **Vector Search & RAG**: Extensible vector store with local TF-IDF semantic embeddings + OpenAI embeddings support

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ (Node 20+ recommended)
- Git

### 2. Backend Setup

```bash
# Clone the repository
git clone https://github.com/abdulrahmanrifayath/Docpilot-AI.git
cd Docpilot-AI

# Create Python virtual environment
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Run automated test suite
pytest backend/tests -v

# Start FastAPI backend server
cd backend
uvicorn app.main:app --reload --port 8000
```
Backend API interactive documentation is available at: `http://localhost:8000/docs`

### 3. Frontend Setup

```bash
# In a new terminal window
cd frontend

# Install npm dependencies
npm install

# Start Vite development server
npm run dev
```
Open `http://localhost:3000` in your web browser.

---

## 🧪 Testing

Run all backend tests with Pytest:
```bash
pytest backend/tests -v
```

Build the frontend bundle:
```bash
cd frontend && npm run build
```

---

## 🐳 Docker Deployment

Run with Docker Compose:
```bash
docker-compose up --build
```

---

## 🛡️ License

MIT License. Designed and engineered for software teams worldwide.
