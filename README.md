# OmniCode

> **Omnicode** is an intelligent developer research assistant and codebase comprehension platform. It indexes multi-language repositories, performs AST-aware chunking, builds vector embeddings, maps architectural dependencies via Mermaid diagrams, and exposes Model Context Protocol (MCP) tooling.

---

## 🌟 Key Features

- **AST-Aware Repository Indexing:** Recursively parses Go, Python, TypeScript, JavaScript, Java, and C# files with symbol-level chunking (classes, methods, functions).
- **Semantic & Hybrid Code Search:** Combines vector embeddings with Qdrant vector database storage and local offline fallback search.
- **Interactive Code Explainer:** Ask deep architectural questions across multiple services and files with cited code references.
- **Dynamic Mermaid Architecture Diagrams:** Automatically generates system architecture, sequence, and class diagrams.
- **Refactoring & Code Smells Auditor:** Pinpoints duplicate code, oversized functions, and bad patterns with actionable diffs.
- **MCP Layer (Model Context Protocol):**
  - **Git MCP:** Inspect commit history, branches, and generate PR drafts.
  - **Database MCP:** Inspect SQL table schemas and query explanations.
  - **Issue Tracker MCP:** Query and track bugs and feature requests.

---

## 🏗️ Architecture

```
Frontend (Next.js 16 + Tailwind CSS + Shadcn UI)
       │
       ▼
API Gateway (Go / Gin - Port 8080)
       │
   ┌───┼─────────────────────────┐
   ▼   ▼                         ▼
Repo Service    Search Service   User Service
(Go - Port 8081) (Go - Port 8082) (Go - Port 8083)
   │               │
   └───────┬───────┘
           ▼
Python AI Engine (FastAPI - Port 8000)
   ├── AST Parser & Chunker
   ├── Qdrant Vector Store
   └── MCP Tool Servers (Git, DB, Jira)
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Node.js** 18+ and **npm**
- **Go** 1.22+
- **Python** 3.10+

### 2. Environment Setup
Copy the example environment file:
```bash
cp .env.example .env
```
Add your `OPENAI_API_KEY` in `.env`.

### 3. Running the Python AI Engine
```bash
cd ai-engine
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
python main.py
```
*Listens on `http://localhost:8000`.*

### 4. Running the Go Backend Services
```bash
cd backend
go run main.go
```
*Listens on `http://localhost:8080` (API Gateway).*

### 5. Running the Frontend
```bash
cd frontend
npm install
npm run dev
```
*Access the UI at `http://localhost:3000`.*

---

## 📄 License
MIT
