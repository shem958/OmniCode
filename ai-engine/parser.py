import os
import re
from typing import List, Dict, Any

class CodeChunker:
    @staticmethod
    def get_language(file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        mapping = {
            '.py': 'python',
            '.go': 'go',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cs': 'csharp',
        }
        return mapping.get(ext, 'unknown')

    @staticmethod
    def chunk_python(content: str, file_path: str) -> List[Dict[str, Any]]:
        lines = content.splitlines()
        chunks = []
        
        # Regex to match class or function definitions
        class_func_pattern = re.compile(r'^(?P<indent>\s*)(?P<type>class|def)\s+(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)')
        
        i = 0
        n = len(lines)
        
        while i < n:
            line = lines[i]
            match = class_func_pattern.match(line)
            if match:
                indent = len(match.group('indent'))
                chunk_type = match.group('type')
                name = match.group('name')
                start_line = i + 1
                
                # Find where the block ends (when indentation is equal or less than start line's,
                # skipping empty lines and comments)
                end_line = start_line
                j = i + 1
                while j < n:
                    next_line = lines[j]
                    # Skip empty lines or comment-only lines in indentation check
                    if not next_line.strip() or next_line.strip().startswith('#'):
                        j += 1
                        continue
                    
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent <= indent:
                        break
                    
                    end_line = j + 1
                    j += 1
                
                # Backtrack to exclude trailing blank lines
                while end_line > start_line and not lines[end_line - 1].strip():
                    end_line -= 1
                
                chunk_content = '\n'.join(lines[start_line - 1:end_line])
                chunks.append({
                    'file_path': file_path,
                    'name': name,
                    'type': 'class' if chunk_type == 'class' else 'function',
                    'content': chunk_content,
                    'start_line': start_line,
                    'end_line': end_line,
                    'language': 'python'
                })
                i = j - 1
            i += 1
            
        # Add a whole-file module fallback chunk if no chunks found, or to keep full context
        if not chunks and content.strip():
            chunks.append({
                'file_path': file_path,
                'name': os.path.basename(file_path),
                'type': 'module',
                'content': content,
                'start_line': 1,
                'end_line': n,
                'language': 'python'
            })
            
        return chunks

    @staticmethod
    def chunk_brace_language(content: str, file_path: str, lang: str) -> List[Dict[str, Any]]:
        lines = content.splitlines()
        chunks = []
        n = len(lines)
        
        # Patterns for different languages
        patterns = {
            'go': [
                re.compile(r'^\s*func\s+(?:\([^)]+\)\s+)?(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\s*\('),
                re.compile(r'^\s*type\s+(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\s+struct\s*\{')
            ],
            'javascript': [
                re.compile(r'^\s*(?:export\s+)?(?:default\s+)?class\s+(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)'),
                re.compile(r'^\s*(?:export\s+)?(?:async\s+)?function\s+(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)'),
                re.compile(r'^\s*(?:export\s+)?(?:const|let|var)\s+(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>')
            ],
            'typescript': [
                re.compile(r'^\s*(?:export\s+)?(?:default\s+)?(?:class|interface|type)\s+(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)'),
                re.compile(r'^\s*(?:export\s+)?(?:async\s+)?function\s+(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)'),
                re.compile(r'^\s*(?:export\s+)?(?:const|let|var)\s+(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*(?::\s*[^=]+)?=>')
            ],
            'java': [
                re.compile(r'^\s*(?:public|protected|private|static|\s)*class\s+(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)'),
                re.compile(r'^\s*(?:public|protected|private|static|\s)+(?P<ret>[a-zA-Z0-9_<>[\]]+)\s+(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\s*\(')
            ],
            'csharp': [
                re.compile(r'^\s*(?:public|internal|private|protected|static|\s)*class\s+(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)'),
                re.compile(r'^\s*(?:public|internal|private|protected|static|\s)+(?P<ret>[a-zA-Z0-9_<>[\]]+)\s+(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\s*\(')
            ]
        }
        
        lang_patterns = patterns.get(lang, [])
        i = 0
        while i < n:
            line = lines[i]
            matched = False
            
            for pattern in lang_patterns:
                match = pattern.match(line)
                if match:
                    name = match.group('name')
                    # Ignore common words that regex might catch in methods
                    if name in ('if', 'for', 'while', 'switch', 'return', 'catch', 'new'):
                        continue
                        
                    start_line = i + 1
                    
                    # Find open brace and count nested braces to find matching close brace
                    brace_count = 0
                    found_first_brace = False
                    j = i
                    
                    while j < n:
                        curr_line = lines[j]
                        # Count braces
                        for char in curr_line:
                            if char == '{':
                                brace_count += 1
                                found_first_brace = True
                            elif char == '}':
                                brace_count -= 1
                                
                        if found_first_brace and brace_count <= 0:
                            break
                        j += 1
                    
                    end_line = min(j + 1, n)
                    chunk_content = '\n'.join(lines[start_line - 1:end_line])
                    
                    # Deduce structural chunk type
                    chunk_type = 'function'
                    if 'class' in line or 'struct' in line or 'interface' in line:
                        chunk_type = 'class'
                        
                    chunks.append({
                        'file_path': file_path,
                        'name': name,
                        'type': chunk_type,
                        'content': chunk_content,
                        'start_line': start_line,
                        'end_line': end_line,
                        'language': lang
                    })
                    i = j
                    matched = True
                    break
            if not matched:
                i += 1
                
        # Add a whole-file module fallback chunk if no chunks found, or to keep full context
        if not chunks and content.strip():
            chunks.append({
                'file_path': file_path,
                'name': os.path.basename(file_path),
                'type': 'module',
                'content': content,
                'start_line': 1,
                'end_line': n,
                'language': lang
            })
            
        return chunks

    @classmethod
    def chunk_file(cls, file_content: str, file_path: str) -> List[Dict[str, Any]]:
        lang = cls.get_language(file_path)
        if lang == 'python':
            return cls.chunk_python(file_content, file_path)
        elif lang in ('go', 'javascript', 'typescript', 'java', 'csharp'):
            return cls.chunk_brace_language(file_content, file_path, lang)
        else:
            # Markdown, plain text, etc. - Treat entire file as one module chunk
            lines = file_content.splitlines()
            return [{
                'file_path': file_path,
                'name': os.path.basename(file_path),
                'type': 'document' if file_path.endswith(('.md', '.txt')) else 'code',
                'content': file_content,
                'start_line': 1,
                'end_line': max(len(lines), 1),
                'language': 'plaintext'
            }]
