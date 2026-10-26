import os
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from parser import CodeChunker
from vector_store import VectorStore
from agent import CodebaseAgent
from mcp_tools import MCPTools

app = FastAPI(title="Developer Research Assistant AI Engine", version="1.0.0")

# Allow CORS for Next.js UI and Go Gateway
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize singletons
vector_store = VectorStore()
agent = CodebaseAgent()
mcp = MCPTools()

# Pydantic models
class IndexRequest(BaseModel):
    directory_path: str
    exclude_dirs: Optional[List[str]] = ["node_modules", ".git", "__pycache__", "venv", ".venv", ".next", "dist", "build", "qdrant_storage", "postgres_data"]

class QueryRequest(BaseModel):
    query: str

class DiagramRequest(BaseModel):
    diagram_type: str # classDiagram, flowchart, sequenceDiagram
    topic: str

# MCP request models
class GitPRRequest(BaseModel):
    repo_path: str
    title: str
    source_branch: str
    target_branch: str

class DocGenRequest(BaseModel):
    repo_path: str
    file_path: str

class ReadmeRequest(BaseModel):
    repo_path: str
    project_summary: str

class IssueCreateRequest(BaseModel):
    title: str
    description: str
    ticket_type: Optional[str] = "Bug"

@app.get("/health")
def health():
    return {"status": "ok", "qdrant_mode": os.getenv("QDRANT_MODE", "local")}

@app.post("/index")
def index_directory(req: IndexRequest):
    if not os.path.exists(req.directory_path):
        raise HTTPException(status_code=400, detail=f"Directory path '{req.directory_path}' does not exist on this machine.")
        
    print(f"[AI-Engine] Indexing directory: {req.directory_path}")
    all_chunks = []
    
    for root, dirs, files in os.walk(req.directory_path):
        # Filter excluded directories in-place
        if req.exclude_dirs:
            dirs[:] = [d for d in dirs if d not in req.exclude_dirs]
            
        for file in files:
            file_path = os.path.join(root, file)
            # Get relative path for clean referencing
            rel_path = os.path.relpath(file_path, req.directory_path).replace("\\", "/")
            
            # Read and chunk supported files
            lang = CodeChunker.get_language(file_path)
            # Also read Markdown / TXT files
            is_supported = lang != 'unknown' or file.endswith(('.md', '.txt', '.json', '.yaml', '.yml'))
            
            if is_supported:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        
                    file_chunks = CodeChunker.chunk_file(content, rel_path)
                    all_chunks.extend(file_chunks)
                except Exception as e:
                    print(f"[AI-Engine] Failed to read/chunk file {rel_path}: {e}")
                    
    if not all_chunks:
        return {"status": "success", "message": "No indexable files found.", "chunks_count": 0}
        
    print(f"[AI-Engine] Found {len(all_chunks)} chunks to embed.")
    
    # Save to Qdrant
    vector_store.add_chunks(all_chunks)
    
    return {
        "status": "success",
        "message": f"Successfully indexed directory. Created {len(all_chunks)} chunks.",
        "chunks_count": len(all_chunks)
    }

@app.post("/query")
def query_codebase(req: QueryRequest):
    try:
        result = agent.answer_question(req.query, vector_store)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/diagram")
def generate_diagram(req: DiagramRequest):
    try:
        result = agent.generate_diagram(req.diagram_type, req.topic, vector_store)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/refactor")
def audit_codebase():
    try:
        result = agent.analyze_refactoring(vector_store)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/architecture")
def detect_architecture():
    try:
        result = agent.detect_architecture(vector_store)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/clear")
def clear_index():
    try:
        vector_store.clear()
        return {"status": "success", "message": "Index cleared successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# MCP ROUTING ENDPOINTS
# ==========================================
@app.get("/api/mcp/git/branches")
def mcp_git_branches(repo_path: str):
    return {"branches": mcp.list_branches(repo_path)}

@app.get("/api/mcp/git/commits")
def mcp_git_commits(repo_path: str, limit: Optional[int] = 5):
    return {"commits": mcp.show_commit_history(repo_path, limit)}

@app.post("/api/mcp/git/pr")
def mcp_git_pr(req: GitPRRequest):
    return mcp.create_pull_request(req.repo_path, req.title, req.source_branch, req.target_branch)

@app.post("/api/mcp/docs/generate")
def mcp_docs_generate(req: DocGenRequest):
    res = mcp.generate_docs(req.repo_path, req.file_path)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@app.post("/api/mcp/docs/readme")
def mcp_docs_readme(req: ReadmeRequest):
    res = mcp.update_readme(req.repo_path, req.project_summary)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@app.get("/api/mcp/db/schema")
def mcp_db_schema(repo_path: str, table_name: str):
    res = mcp.schema_lookup(repo_path, table_name)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

@app.post("/api/mcp/issues/create")
def mcp_issues_create(req: IssueCreateRequest):
    res = mcp.create_ticket(req.title, req.description, req.ticket_type)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@app.get("/api/mcp/issues/bugs")
def mcp_issues_bugs():
    return {"bugs": mcp.list_bugs()}

@app.get("/api/mcp/issues/features")
def mcp_issues_features():
    return {"feature_requests": mcp.find_feature_requests()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
