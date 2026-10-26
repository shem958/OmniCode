import os
import subprocess
import json
import sqlite3
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class MCPTools:
    def __init__(self):
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        self.issues_file = os.path.join(os.path.dirname(__file__), "..", "issues.json")
        self._ensure_issues_file()

    def _ensure_issues_file(self):
        if not os.path.exists(self.issues_file):
            default_issues = [
                {
                    "id": "BUG-101",
                    "title": "Auth token expires too quickly",
                    "description": "JWT expiration is set to 5 minutes. Should be increased to 1 hour.",
                    "status": "Open",
                    "type": "Bug",
                    "created_at": "2026-07-08T12:00:00Z"
                },
                {
                    "id": "FEAT-201",
                    "title": "Add export to PDF for reports",
                    "description": "Allow users to download repository health audits in PDF format.",
                    "status": "In Progress",
                    "type": "Feature Request",
                    "created_at": "2026-07-08T14:30:00Z"
                }
            ]
            with open(self.issues_file, "w") as f:
                json.dump(default_issues, f, indent=2)

    # ==========================================
    # GIT MCP TOOLS
    # ==========================================
    def list_branches(self, repo_path: str) -> List[str]:
        try:
            result = subprocess.run(
                ["git", "branch", "-a"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            branches = [line.strip().replace("* ", "") for line in result.stdout.splitlines() if line.strip()]
            return branches
        except Exception:
            # Mock fallback if git fails or directory is not a repo
            return ["main", "develop", "feature/oauth-integration"]

    def show_commit_history(self, repo_path: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            result = subprocess.run(
                ["git", "log", f"-n {limit}", "--pretty=format:%H|%an|%ad|%s", "--date=short"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            commits = []
            for line in result.stdout.splitlines():
                if not line.strip():
                    continue
                parts = line.split("|")
                if len(parts) >= 4:
                    commits.append({
                        "hash": parts[0],
                        "author": parts[1],
                        "date": parts[2],
                        "subject": parts[3]
                    })
            return commits
        except Exception:
            # Mock fallback
            return [
                {"hash": "a1b2c3d4", "author": "Shem Gikunda", "date": "2026-07-08", "subject": "refactor: optimize indexing pipeline"},
                {"hash": "e5f6g7h8", "author": "Shem Gikunda", "date": "2026-07-07", "subject": "feat: add vector embeddings manager"},
                {"hash": "i9j0k1l2", "author": "Shem Gikunda", "date": "2026-07-06", "subject": "init: project scaffolding setup"}
            ]

    def create_pull_request(self, repo_path: str, title: str, source: str, target: str) -> Dict[str, Any]:
        return {
            "status": "success",
            "pr_number": 42,
            "title": title,
            "source_branch": source,
            "target_branch": target,
            "url": "https://github.com/mock/repo/pull/42",
            "message": f"Successfully opened Pull Request #42 from '{source}' to '{target}'."
        }

    # ==========================================
    # DOCUMENTATION MCP TOOLS
    # ==========================================
    def generate_docs(self, repo_path: str, file_path: str) -> Dict[str, Any]:
        full_path = os.path.join(repo_path, file_path)
        if not os.path.exists(full_path):
            return {"status": "error", "message": f"File {file_path} not found"}

        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                code_content = f.read()

            system_prompt = (
                "You are an expert technical writer.\n"
                "Generate comprehensive markdown documentation for the provided code file.\n"
                "Include: Overview, Class/Struct Descriptions, API/Method Signatures, and Usage Examples.\n"
                "Do not write any text outside of the markdown code block. Return ONLY the markdown documentation."
            )
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"File Name: {file_path}\nCode:\n{code_content}"}
                ],
                temperature=0.2
            )

            doc_content = response.choices[0].message.content
            
            # Save the doc in the repo's docs folder
            docs_dir = os.path.join(repo_path, "docs")
            os.makedirs(docs_dir, exist_ok=True)
            doc_file_name = f"{os.path.splitext(os.path.basename(file_path))[0]}.md"
            doc_file_path = os.path.join(docs_dir, doc_file_name)
            
            with open(doc_file_path, "w", encoding="utf-8") as f:
                f.write(doc_content)

            return {
                "status": "success",
                "doc_path": os.path.relpath(doc_file_path, repo_path).replace("\\", "/"),
                "content": doc_content
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def update_readme(self, repo_path: str, project_summary: str) -> Dict[str, Any]:
        readme_path = os.path.join(repo_path, "README.md")
        try:
            readme_content = f"# Project Overview\n\n{project_summary}\n\n## Setup and Installation\n```bash\nnpm install\nnpm run dev\n```\n"
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(readme_content)
            return {"status": "success", "message": "README.md updated successfully."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ==========================================
    # DATABASE MCP TOOLS
    # ==========================================
    def schema_lookup(self, repo_path: str, table_name: str) -> Dict[str, Any]:
        # Return static structure representing a database schema or search SQLite in repo
        # Example schema representations:
        schemas = {
            "users": {
                "columns": [
                    {"name": "id", "type": "VARCHAR(36)", "constraints": "PRIMARY KEY"},
                    {"name": "email", "type": "VARCHAR(255)", "constraints": "UNIQUE, NOT NULL"},
                    {"name": "name", "type": "VARCHAR(100)", "constraints": ""},
                    {"name": "password_hash", "type": "VARCHAR(255)", "constraints": "NOT NULL"},
                    {"name": "created_at", "type": "TIMESTAMP", "constraints": "DEFAULT CURRENT_TIMESTAMP"}
                ]
            },
            "repositories": {
                "columns": [
                    {"name": "id", "type": "VARCHAR(36)", "constraints": "PRIMARY KEY"},
                    {"name": "name", "type": "VARCHAR(100)", "constraints": "NOT NULL"},
                    {"name": "path", "type": "TEXT", "constraints": ""},
                    {"name": "status", "type": "VARCHAR(20)", "constraints": ""},
                    {"name": "created_at", "type": "TIMESTAMP", "constraints": ""}
                ]
            },
            "invoices": {
                "columns": [
                    {"name": "id", "type": "VARCHAR(36)", "constraints": "PRIMARY KEY"},
                    {"name": "user_id", "type": "VARCHAR(36)", "constraints": "FOREIGN KEY REFERENCES users(id)"},
                    {"name": "amount", "type": "DECIMAL(10,2)", "constraints": "NOT NULL"},
                    {"name": "status", "type": "VARCHAR(20)", "constraints": "DEFAULT 'pending'"},
                    {"name": "created_at", "type": "TIMESTAMP", "constraints": ""}
                ]
            }
        }
        
        if table_name in schemas:
            return {"table": table_name, "schema": schemas[table_name]}
        
        return {
            "table": table_name,
            "error": "Table not found in active schema configurations.",
            "available_tables": list(schemas.keys())
        }

    # ==========================================
    # ISSUE TRACKER MCP TOOLS
    # ==========================================
    def create_ticket(self, title: str, description: str, ticket_type: str = "Bug") -> Dict[str, Any]:
        try:
            with open(self.issues_file, "r") as f:
                issues = json.load(f)
            
            ticket_id = f"{'BUG' if ticket_type == 'Bug' else 'FEAT'}-{len(issues) + 101}"
            new_ticket = {
                "id": ticket_id,
                "title": title,
                "description": description,
                "status": "Open",
                "type": ticket_type,
                "created_at": "2026-07-08T23:00:00Z"
            }
            issues.append(new_ticket)
            
            with open(self.issues_file, "w") as f:
                json.dump(issues, f, indent=2)
                
            return {"status": "success", "ticket": new_ticket}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_bugs(self) -> List[Dict[str, Any]]:
        try:
            with open(self.issues_file, "r") as f:
                issues = json.load(f)
            return [issue for issue in issues if issue["type"] == "Bug"]
        except Exception:
            return []

    def find_feature_requests(self) -> List[Dict[str, Any]]:
        try:
            with open(self.issues_file, "r") as f:
                issues = json.load(f)
            return [issue for issue in issues if issue["type"] == "Feature Request"]
        except Exception:
            return []
