#!/usr/bin/env python3
"""
Dynamic Code Modifier with LLM Integration
Reads existing codebase, picks random lines, and makes real improvements
"""

import os
import subprocess
import json
import logging
import random
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import openai

class DynamicCodeModifier:
    def __init__(self, config_file: str = "dynamic_commit_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.setup_logging()
        self.setup_openai()
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_dir = Path.home() / ".local" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "dynamic_commits.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_openai(self):
        """Setup OpenAI client"""
        import os
        
        # Try to get API key from environment first, then config
        api_key = os.getenv('OPENAI_API_KEY') or self.config.get("openai_api_key")
        
        if not api_key or api_key == "PLACEHOLDER_WILL_BE_SET_BY_ENV":
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        
        openai.api_key = api_key
        self.client = openai
    def load_config(self) -> Dict:
        """Load configuration from JSON file"""
        print(f"DEBUG: Looking for config file: {self.config_file}")
        print(f"DEBUG: Config file exists: {os.path.exists(self.config_file)}") 
        
        default_config = {
            "repositories": [],
            "openai_api_key": "",
            "file_extensions": [".ts", ".js", ".tsx", ".jsx", ".py", ".java", ".go", ".rs"],
            "ignore_patterns": ["node_modules", ".git", "dist", "build", "__pycache__"],
            "modification_types": [
                "improve_performance",
                "add_error_handling", 
                "improve_readability",
                "add_documentation",
                "optimize_code",
                "add_type_safety",
                "refactor_logic"
            ],
            "max_tokens": 150,
            "temperature": 0.3
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                print(f"DEBUG: Loaded config keys: {list(user_config.keys())}")
                print(f"DEBUG: Has openai_api_key: {'openai_api_key' in user_config}")
                if 'openai_api_key' in user_config:
                    key = user_config['openai_api_key']
                    print(f"DEBUG: API key length: {len(key)}")
                    print(f"DEBUG: API key starts with: {key[:10]}...")
                default_config.update(user_config)
                print(f"DEBUG: Final config has API key: {'openai_api_key' in default_config}")
            except Exception as e:
                print(f"DEBUG: Error loading config: {e}")
                self.logger.error(f"Error loading config: {e}")
        else:
            self.save_config(default_config)
            
        return default_config

    def save_config(self, config: Dict):
        """Save configuration to JSON file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")

    def run_git_command(self, repo_path: str, command: List[str]) -> Tuple[bool, str]:
        """Run git command in specified repository"""
        try:
            result = subprocess.run(
                ['git'] + command,
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return False, e.stderr.strip()

    def find_code_files(self, repo_path: str) -> List[Path]:
        """Find all code files in repository recursively"""
        code_files = []
        repo = Path(repo_path)
        
        extensions = self.config.get("file_extensions", [])
        ignore_patterns = self.config.get("ignore_patterns", [])
        
        print(f"DEBUG: Searching in {repo_path}")
        print(f"DEBUG: Looking for extensions: {extensions}")
        
        # Search recursively through all subdirectories
        for ext in extensions:
            for file_path in repo.rglob(f"*{ext}"):
                file_str = str(file_path)
                
                # Skip ignored patterns
                if any(pattern in file_str for pattern in ignore_patterns):
                    print(f"DEBUG: Skipping {file_path} (matches ignore pattern)")
                    continue
                
                # Skip virtual environment files specifically
                if any(skip in file_str for skip in ['venv', 'site-packages', '.git', 'node_modules']):
                    print(f"DEBUG: Skipping {file_path} (system/env file)")
                    continue
                    
                # Skip very small or very large files
                file_size = file_path.stat().st_size
                if file_size < 50 or file_size > 50000:
                    print(f"DEBUG: Skipping {file_path} (size: {file_size} bytes)")
                    continue
                
                print(f"DEBUG: Found valid file: {file_path} ({file_size} bytes)")
                code_files.append(file_path)
        
        print(f"DEBUG: Total files found: {len(code_files)}")
        if code_files:
            print(f"DEBUG: First few files: {[str(f) for f in code_files[:5]]}")
        
        return code_files

    def select_random_code_section(self, file_path: Path) -> Optional[Dict]:
        """Select a random code section to modify"""
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            # Filter out empty lines and comments
            meaningful_lines = []
            for i, line in enumerate(lines):
                stripped = line.strip()
                if (stripped and 
                    not stripped.startswith('//') and 
                    not stripped.startswith('#') and
                    not stripped.startswith('/*') and
                    not stripped.startswith('*') and
                    len(stripped) > 10):
                    meaningful_lines.append((i, line))
            
            if len(meaningful_lines) < 3:
                return None
                
            # Select random section (3-8 lines)
            section_size = random.randint(2, min(3, len(meaningful_lines)))
            start_idx = random.randint(0, len(meaningful_lines) - section_size)
            
            selected_lines = meaningful_lines[start_idx:start_idx + section_size]
            
            return {
                'file_path': file_path,
                'lines': selected_lines,
                'content': content,
                'all_lines': lines,
                'language': self.detect_language(file_path)
            }
            
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            return None

    def detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension"""
        ext = file_path.suffix.lower()
        language_map = {
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.js': 'javascript', 
            '.jsx': 'javascript',
            '.py': 'python',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust'
        }
        return language_map.get(ext, 'unknown')

    def get_improvement_prompt(self, code_section: Dict, modification_type: str) -> str:
        """Generate prompt for LLM to improve code"""
        language = code_section['language']
        code_lines = [line[1] for line in code_section['lines']]
        code_text = '\n'.join(code_lines)
        
        prompts = {
            "improve_performance": f"Improve the performance of this {language} code. Only return the improved code, no explanations:\n\n{code_text}",
            
            "add_error_handling": f"Add proper error handling to this {language} code. Only return the improved code, no explanations:\n\n{code_text}",
            
            "improve_readability": f"Make this {language} code more readable and clean. Only return the improved code, no explanations:\n\n{code_text}",
                        
            "optimize_code": f"Optimize this {language} code for better efficiency. Only return the improved code, no explanations:\n\n{code_text}",
        }
        
        return prompts.get(modification_type, prompts["improve_readability"])

    def call_openai(self, prompt: str) -> Optional[str]:
        """Call OpenAI API to improve code"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a senior software engineer. Improve the given code and return ONLY the improved code, no explanations or markdown formatting."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config.get("max_tokens", 150),
                temperature=self.config.get("temperature", 0.3)
            )
            
            content = response.choices[0].message.content
            if not content:
                self.logger.error("OpenAI response content was empty")
                return None
            improved_code = content.strip()            
            # Clean up response (remove markdown formatting if present)
            improved_code = re.sub(r'^```\w*\n?', '', improved_code)
            improved_code = re.sub(r'\n?```$', '', improved_code)
            
            return improved_code
            
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            return None

    def apply_code_modification(self, code_section: Dict, improved_code: str) -> bool:
        """Apply the improved code to the file"""
        try:
            file_path = code_section['file_path']
            all_lines = code_section['all_lines']
            selected_lines = code_section['lines']
            
            # Get line numbers to replace
            start_line = selected_lines[0][0]
            end_line = selected_lines[-1][0]
            
            # Split improved code into lines
            new_lines = improved_code.split('\n')
            
            # Replace the section
            modified_lines = (
                all_lines[:start_line] + 
                new_lines + 
                all_lines[end_line + 1:]
            )
            
            # Write back to file
            modified_content = '\n'.join(modified_lines)
            file_path.write_text(modified_content, encoding='utf-8')
            
            self.logger.info(f"Modified {file_path} (lines {start_line}-{end_line})")
            return True
            
        except Exception as e:
            self.logger.error(f"Error applying modification: {e}")
            return False

    def generate_commit_message(self, modification_type: str, file_path: Path) -> str:
        """Generate professional commit message"""
        messages = {
            "improve_performance": "perf: optimize code performance",
            "add_error_handling": "fix: improve error handling",
            "improve_readability": "refactor: improve code readability", 
            "add_documentation": "docs: add code comments",
            "optimize_code": "perf: optimize implementation",
            "add_type_safety": "feat: enhance type safety",
            "refactor_logic": "refactor: simplify logic"
        }
        
        return messages.get(modification_type, "chore: improve code quality")

    def make_dynamic_commit(self, repo_path: str) -> Tuple[bool, str]:
        """Make a dynamic commit by modifying existing code"""
        try:
            # Find all code files
            code_files = self.find_code_files(repo_path)
            if not code_files:
                return False, "No suitable code files found"
            
            # Filter to only existing source files (not generated ones)
            existing_files = []
            for file_path in code_files:
                # Skip our generated files
                if any(skip in str(file_path) for skip in ['fixes', 'features', 'performance', 'security']):
                    continue
                # Only include files that already have meaningful content
                if file_path.stat().st_size > 200:  # At least 200 bytes
                    existing_files.append(file_path)
            
            if not existing_files:
                return False, "No existing source files found to modify"
            
            # Try up to 5 random existing files
            for attempt in range(5):
                random_file = random.choice(existing_files)
                self.logger.info(f"Attempting to modify existing file: {random_file}")
                
                # Select random code section
                code_section = self.select_random_code_section(random_file)
                if not code_section:
                    continue
                
                # Choose modification type
                modification_type = random.choice(self.config.get("modification_types", []))
                
                # Generate improvement prompt
                prompt = self.get_improvement_prompt(code_section, modification_type)
                
                # Get improved code from LLM
                improved_code = self.call_openai(prompt)
                if not improved_code:
                    continue
                
                # Validate that the improved code is actually different
                original_code = '\n'.join([line[1] for line in code_section['lines']])
                if improved_code.strip() == original_code.strip():
                    continue
                
                # Apply the modification to the existing file
                if self.apply_code_modification(code_section, improved_code):
                    # Generate professional commit message (no filename)
                    commit_message = self.generate_commit_message(modification_type, random_file)
                    
                    # Commit and push
                    return self.commit_and_push(repo_path, commit_message)
            
            return False, "Could not generate suitable modifications after 5 attempts"
            
        except Exception as e:
            return False, f"Error in dynamic commit: {str(e)}"

    def commit_and_push(self, repo_path: str, commit_message: str) -> Tuple[bool, str]:
        """Commit and push changes"""
        try:
            # Stage all changes
            success, output = self.run_git_command(repo_path, ['add', '.'])
            if not success:
                return False, f"Failed to stage files: {output}"
            
            # Check if there are changes to commit
            success, output = self.run_git_command(repo_path, ['diff', '--cached', '--name-only'])
            if not success or not output.strip():
                return False, "No changes to commit"
            
            # Commit changes
            success, output = self.run_git_command(repo_path, ['commit', '-m', commit_message])
            if not success:
                return False, f"Failed to commit: {output}"
            
            # Push to remote
            success, output = self.run_git_command(repo_path, ['push'])
            if not success:
                return False, f"Failed to push: {output}"
                
            self.logger.info(f"Successfully committed and pushed: {commit_message}")
            return True, commit_message
            
        except Exception as e:
            return False, f"Error during commit process: {str(e)}"

    def run_dynamic_commits(self):
        """Run dynamic commits for all configured repositories"""
        self.logger.info("Starting dynamic code modifier")
        
        repositories = self.config.get("repositories", [])
        if not repositories:
            self.logger.warning("No repositories configured")
            return {}
            
        results = {}
        for repo_path in repositories:
            try:
                success, message = self.make_dynamic_commit(repo_path)
                results[repo_path] = {
                    "success": success,
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                }
                
                if success:
                    self.logger.info(f"✅ Dynamic commit made to {repo_path}: {message}")
                else:
                    self.logger.error(f"❌ Failed to commit to {repo_path}: {message}")
                    
            except Exception as e:
                self.logger.error(f"Error processing {repo_path}: {e}")
                results[repo_path] = {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        # Log summary
        successful = sum(1 for r in results.values() if r.get("success"))
        failed = len(results) - successful
        
        self.logger.info(f"Dynamic commit summary: {successful} successful, {failed} failed")
        return results

def main():
    """Main function to run the dynamic modifier"""
    modifier = DynamicCodeModifier()
    modifier.run_dynamic_commits()

if __name__ == "__main__":
    main()


#   "repositories": [
#     "/Users/apple/Desktop/raycast-image-finder",
#     "/Users/apple/Desktop/bitnile-backend-app",
#     "/Users/apple/Downloads/Archive/buick-animation-backend/wishoo-buick-animation-backend/wishoo-buick-animation-backend",
#     "/Users/apple/Downloads/Archive/Duett",
#     "/Users/apple/Downloads/Archive/just-a-moment",
#     "/Users/apple/Downloads/Archive/MOC",
#     "/Users/apple/Downloads/Archive/upnext",
#     "/Users/apple/Downloads/Archive/wishoo-electrify",
#     "/Users/apple/Downloads/Archive/wishoo-hummer-vegas"
#   ],