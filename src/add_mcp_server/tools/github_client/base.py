import os
import requests
import re
from typing import Dict, List, Any, Optional, Iterator


class GitHubException(Exception):
    """GitHub API Exception"""
    pass


class GitHubClient:
    """Base GitHub API Client with authentication and pagination."""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv('GITHUB_TOKEN')
        if not self.token:
            raise GitHubException("GitHub token required. Set GITHUB_TOKEN environment variable.")
        
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "MCP-GitHub-Client/1.0"
        })
    
    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make authenticated request to GitHub API."""
        url = f"{self.base_url}{endpoint}" if endpoint.startswith('/') else f"{self.base_url}/{endpoint}"
        
        response = self.session.request(method, url, **kwargs)
        
        if response.status_code >= 400:
            try:
                error_data = response.json()
                message = error_data.get('message', f'HTTP {response.status_code}')
                raise GitHubException(f"GitHub API Error: {message}")
            except ValueError:
                raise GitHubException(f"GitHub API Error: HTTP {response.status_code}")
        
        return response
    
    def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """GET request returning JSON."""
        response = self._request('GET', endpoint, **kwargs)
        return response.json()
    
    def post(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """POST request returning JSON."""
        response = self._request('POST', endpoint, **kwargs)
        return response.json()
    
    def patch(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """PATCH request returning JSON."""
        response = self._request('PATCH', endpoint, **kwargs)
        return response.json()
    
    def delete(self, endpoint: str, **kwargs) -> bool:
        """DELETE request returning success status."""
        response = self._request('DELETE', endpoint, **kwargs)
        return response.status_code in [200, 204]
    
    def paginate(self, endpoint: str, **kwargs) -> Iterator[Dict[str, Any]]:
        """Paginate through all results from an endpoint."""
        url = f"{self.base_url}{endpoint}" if endpoint.startswith('/') else f"{self.base_url}/{endpoint}"
        
        while url:
            response = self._request('GET', url, **kwargs)
            data = response.json()
            
            # Yield each item
            if isinstance(data, list):
                for item in data:
                    yield item
            else:
                yield data
                break
            
            # Get next URL from Link header
            url = None
            link_header = response.headers.get('Link', '')
            if 'rel="next"' in link_header:
                # Parse Link header: <https://api.github.com/...?page=2>; rel="next"
                match = re.search(r'<([^>]+)>;\s*rel="next"', link_header)
                if match:
                    url = match.group(1)
    
    def get_all_pages(self, endpoint: str, **kwargs) -> List[Dict[str, Any]]:
        """Get all paginated results as a list."""
        return list(self.paginate(endpoint, **kwargs))