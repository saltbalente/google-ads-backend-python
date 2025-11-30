"""
Repository Importer - Clone and modify GitHub repositories
Author: System
Date: 2025-11-30
"""

import os
import re
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Dict, List
import requests


class RepositoryImporter:
    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize the repository importer
        
        Args:
            github_token: GitHub personal access token (optional, for private repos)
        """
        self.github_token = github_token or os.environ.get('GITHUB_TOKEN')
        self.temp_dir = None
        
    def import_and_modify(
        self,
        repo_url: str,
        new_repo_name: Optional[str],
        whatsapp_number: str,
        phone_number: Optional[str],
        gtm_id: str
    ) -> Dict[str, str]:
        """
        Clone a repository, modify contact info, and create a new version
        
        Args:
            repo_url: Full GitHub repository URL
            new_repo_name: Name for the new repository (optional)
            whatsapp_number: New WhatsApp number
            phone_number: New phone number (optional)
            gtm_id: New Google Tag Manager ID
            
        Returns:
            Dict with success status, url, and repo name
        """
        try:
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp(prefix='repo_import_')
            
            # Extract repo info
            owner, repo_name = self._parse_github_url(repo_url)
            
            # Determine new repo name
            if not new_repo_name:
                new_repo_name = f"{repo_name}-modified"
            
            # Clone repository
            clone_path = self._clone_repository(repo_url, self.temp_dir)
            
            # Find and modify HTML files
            modified_files = self._modify_html_files(
                clone_path,
                whatsapp_number,
                phone_number,
                gtm_id
            )
            
            # Create new repository on GitHub
            new_repo_url = self._create_github_repo(new_repo_name, owner)
            
            # Push modified code to new repository
            self._push_to_new_repo(clone_path, new_repo_url)
            
            # Cleanup
            self._cleanup()
            
            return {
                'success': True,
                'url': new_repo_url,
                'repoName': new_repo_name,
                'modifiedFiles': len(modified_files),
                'files': modified_files
            }
            
        except Exception as e:
            self._cleanup()
            raise Exception(f"Error importing repository: {str(e)}")
    
    def _parse_github_url(self, url: str) -> tuple:
        """Parse GitHub URL to extract owner and repo name"""
        # Extract owner and repo from URL
        # Supports: https://github.com/owner/repo or git@github.com:owner/repo
        patterns = [
            r'github\.com[:/]([^/]+)/([^/\s]+)',  # More permissive - captures repo name
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                owner = match.group(1)
                repo = match.group(2)
                
                # Remove .git suffix if present (properly)
                if repo.endswith('.git'):
                    repo = repo[:-4]
                
                return owner, repo
        
        raise ValueError("Invalid GitHub URL format")
    
    def _clone_repository(self, repo_url: str, destination: str) -> str:
        """Clone the repository to a temporary location"""
        try:
            # Add token to URL if available for private repos
            if self.github_token and 'https://' in repo_url:
                repo_url = repo_url.replace('https://', f'https://{self.github_token}@')
            
            clone_path = os.path.join(destination, 'repo')
            
            result = subprocess.run(
                ['git', 'clone', repo_url, clone_path],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                raise Exception(f"Git clone failed: {result.stderr}")
            
            return clone_path
            
        except subprocess.TimeoutExpired:
            raise Exception("Clone timeout - repository too large")
        except Exception as e:
            raise Exception(f"Clone failed: {str(e)}")
    
    def _modify_html_files(
        self,
        repo_path: str,
        whatsapp: str,
        phone: Optional[str],
        gtm_id: str
    ) -> List[str]:
        """
        Find and modify all HTML files in the repository
        
        Returns:
            List of modified file paths
        """
        modified_files = []
        
        # Find all HTML files
        html_files = list(Path(repo_path).rglob('*.html'))
        
        for html_file in html_files:
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # Replace WhatsApp numbers
                content = self._replace_whatsapp(content, whatsapp)
                
                # Replace phone numbers if provided
                if phone:
                    content = self._replace_phone(content, phone)
                
                # Replace GTM ID
                content = self._replace_gtm(content, gtm_id)
                
                # Only write if changes were made
                if content != original_content:
                    with open(html_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    # Get relative path for reporting
                    rel_path = os.path.relpath(html_file, repo_path)
                    modified_files.append(rel_path)
                    
            except Exception as e:
                print(f"Warning: Could not modify {html_file}: {str(e)}")
                continue
        
        return modified_files
    
    def _replace_whatsapp(self, content: str, new_number: str) -> str:
        """Replace WhatsApp numbers in HTML content"""
        # Remove any non-digit characters from the new number for wa.me links
        clean_number = re.sub(r'\D', '', new_number)
        
        # Pattern 1: wa.me links
        content = re.sub(
            r'https?://wa\.me/\d+',
            f'https://wa.me/{clean_number}',
            content,
            flags=re.IGNORECASE
        )
        
        # Pattern 2: api.whatsapp.com links
        content = re.sub(
            r'https?://api\.whatsapp\.com/send\?phone=\d+',
            f'https://wa.me/{clean_number}',
            content,
            flags=re.IGNORECASE
        )
        
        # Pattern 2: tel: links with whatsapp class or data-whatsapp
        content = re.sub(
            r'(class=["\'][^"\']*whatsapp[^"\']*["\'][^>]*href=["\'])tel:([^"\']+)(["\'])',
            f'\\1https://wa.me/{clean_number}\\3',
            content,
            flags=re.IGNORECASE
        )
        
        # Pattern 3: Direct phone number display (keep formatting but replace digits)
        # This is more conservative - only replaces in obvious WhatsApp contexts
        whatsapp_contexts = [
            r'(WhatsApp[:\s]+)(\+?\d[\d\s\-()]+)',
            r'(data-whatsapp=["\'][^"\']*["\'][^>]*>)(\+?\d[\d\s\-()]+)',
        ]
        
        for pattern in whatsapp_contexts:
            content = re.sub(
                pattern,
                f'\\1{new_number}',
                content,
                flags=re.IGNORECASE
            )
        
        return content
    
    def _replace_phone(self, content: str, new_number: str) -> str:
        """Replace phone numbers in HTML content"""
        # Clean number for tel: links
        clean_number = re.sub(r'\D', '', new_number)
        
        # Pattern 1: tel: links (not whatsapp-related)
        content = re.sub(
            r'href=["\']tel:(\+?\d[\d\-\s()]+)["\'](?![^<]*whatsapp)',
            f'href="tel:+{clean_number}"',
            content,
            flags=re.IGNORECASE
        )
        
        # Pattern 2: Phone number displays
        phone_contexts = [
            r'(Teléfono[:\s]+)(\+?\d[\d\s\-()]+)',
            r'(Tel[:\s]+)(\+?\d[\d\s\-()]+)',
            r'(Phone[:\s]+)(\+?\d[\d\s\-()]+)',
        ]
        
        for pattern in phone_contexts:
            content = re.sub(
                pattern,
                f'\\1{new_number}',
                content,
                flags=re.IGNORECASE
            )
        
        return content
    
    def _replace_gtm(self, content: str, new_gtm_id: str) -> str:
        """Replace Google Tag Manager ID"""
        # Pattern 1: GTM script tags
        content = re.sub(
            r'GTM-[A-Z0-9]+',
            new_gtm_id,
            content,
            flags=re.IGNORECASE
        )
        
        # Pattern 2: In noscript iframe
        content = re.sub(
            r'(googletagmanager\.com/ns\.html\?id=)GTM-[A-Z0-9]+',
            f'\\1{new_gtm_id}',
            content,
            flags=re.IGNORECASE
        )
        
        return content
    
    def _create_github_repo(self, repo_name: str, owner: str) -> str:
        """Create a new repository on GitHub"""
        if not self.github_token:
            raise Exception("GitHub token required to create repository")
        
        # Create repository via GitHub API
        api_url = "https://api.github.com/user/repos"
        
        headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        data = {
            'name': repo_name,
            'description': 'Modified version with updated contact information',
            'private': False,
            'auto_init': False
        }
        
        response = requests.post(api_url, headers=headers, json=data)
        
        if response.status_code == 201:
            repo_data = response.json()
            return repo_data['html_url']
        elif response.status_code == 422:
            # Repository already exists
            return f"https://github.com/{owner}/{repo_name}"
        else:
            raise Exception(f"Failed to create repository: {response.text}")
    
    def _push_to_new_repo(self, repo_path: str, new_repo_url: str):
        """Push modified code to the new repository"""
        try:
            # Change to repo directory
            original_dir = os.getcwd()
            os.chdir(repo_path)
            
            # Add token to URL if available
            if self.github_token and 'https://' in new_repo_url:
                push_url = new_repo_url.replace('https://', f'https://{self.github_token}@') + '.git'
            else:
                push_url = new_repo_url + '.git'
            
            # Configure git
            subprocess.run(['git', 'config', 'user.email', 'bot@example.com'], check=True)
            subprocess.run(['git', 'config', 'user.name', 'Repository Importer Bot'], check=True)
            
            # Add all changes
            subprocess.run(['git', 'add', '-A'], check=True)
            
            # Check if there are changes to commit
            result = subprocess.run(
                ['git', 'diff', '--staged', '--quiet'],
                capture_output=True
            )
            
            if result.returncode != 0:  # There are changes
                subprocess.run(
                    ['git', 'commit', '-m', 'Update contact information and GTM ID'],
                    check=True
                )
            
            # Remove old origin and add new one
            subprocess.run(['git', 'remote', 'remove', 'origin'], capture_output=True)
            subprocess.run(['git', 'remote', 'add', 'origin', push_url], check=True)
            
            # Push to new repository
            subprocess.run(
                ['git', 'push', '-u', 'origin', 'main', '--force'],
                check=True,
                timeout=120
            )
            
            # Return to original directory
            os.chdir(original_dir)
            
        except subprocess.CalledProcessError as e:
            os.chdir(original_dir)
            raise Exception(f"Git push failed: {str(e)}")
        except subprocess.TimeoutExpired:
            os.chdir(original_dir)
            raise Exception("Push timeout - check network connection")
    
    def _cleanup(self):
        """Remove temporary files"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"Warning: Could not cleanup temp directory: {str(e)}")


def test_importer():
    """Test function to verify the importer works"""
    importer = RepositoryImporter()
    
    # Test URL parsing
    test_urls = [
        "https://github.com/user/repo",
        "https://github.com/user/repo.git",
        "git@github.com:user/repo.git"
    ]
    
    for url in test_urls:
        try:
            owner, repo = importer._parse_github_url(url)
            print(f"✓ Parsed {url} -> {owner}/{repo}")
        except Exception as e:
            print(f"✗ Failed to parse {url}: {str(e)}")


if __name__ == "__main__":
    test_importer()
