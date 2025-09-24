"""
GitBook Tool - Read and search public GitBook documentations
No authentication token required for public docs!
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List
import re
from urllib.parse import urljoin, urlparse


def clean_text(text: str) -> str:
    """Clean and format text from HTML."""
    if not text:
        return ""
    
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    # Remove common GitBook navigation elements
    text = re.sub(r'Table of contents', '', text, flags=re.IGNORECASE)
    text = re.sub(r'On this page', '', text, flags=re.IGNORECASE)
    
    return text


def extract_gitbook_content(html_content: str, url: str) -> Dict[str, Any]:
    """Extract structured content from GitBook page HTML."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Common GitBook selectors
    content_selectors = [
        '[data-testid="page-content"]',  # Main content area
        '.page-body',                    # Alternative content area
        'main',                         # Generic main content
        '.content',                     # Generic content
        'article'                       # Article content
    ]
    
    content = ""
    title = ""
    
    # Try to find the title
    title_selectors = ['h1', '[data-testid="page-title"]', 'title']
    for selector in title_selectors:
        title_elem = soup.select_one(selector)
        if title_elem:
            title = clean_text(title_elem.get_text())
            break
    
    # Try to find the main content
    for selector in content_selectors:
        content_elem = soup.select_one(selector)
        if content_elem:
            # Remove navigation and TOC elements
            for nav in content_elem.select('nav, .toc, .table-of-contents'):
                nav.decompose()
            
            content = clean_text(content_elem.get_text())
            break
    
    # If no structured content found, try to get all text
    if not content:
        # Remove scripts, styles, nav elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer']):
            element.decompose()
        content = clean_text(soup.get_text())
    
    # Extract headings for structure
    headings = []
    for heading in soup.select('h1, h2, h3, h4, h5, h6'):
        headings.append({
            "level": int(heading.name[1]),
            "text": clean_text(heading.get_text()),
            "id": heading.get('id', '')
        })
    
    # Extract links
    links = []
    base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    for link in soup.select('a[href]'):
        href = link.get('href')
        if href and not href.startswith('#'):
            full_url = urljoin(url, href)
            links.append({
                "text": clean_text(link.get_text()),
                "url": full_url,
                "internal": urlparse(full_url).netloc == urlparse(url).netloc
            })
    
    return {
        "title": title,
        "content": content[:5000] if content else "",  # Limit content length
        "headings": headings[:10],  # Limit headings
        "links": links[:20],  # Limit links
        "url": url,
        "word_count": len(content.split()) if content else 0
    }


def search_in_content(content: str, query: str) -> List[str]:
    """Search for query in content and return relevant snippets."""
    if not content or not query:
        return []
    
    # Simple text search with context
    query_lower = query.lower()
    content_lower = content.lower()
    
    matches = []
    words = content.split()
    
    for i, word in enumerate(words):
        if query_lower in word.lower():
            # Get context around the match
            start = max(0, i - 15)
            end = min(len(words), i + 15)
            snippet = ' '.join(words[start:end])
            
            # Highlight the match
            snippet_highlighted = re.sub(
                f'({re.escape(query)})', 
                f'**{query}**', 
                snippet, 
                flags=re.IGNORECASE
            )
            
            matches.append(f"...{snippet_highlighted}...")
    
    return matches[:5]  # Return top 5 matches


def run(operation: str, **params) -> Dict[str, Any]:
    """Execute GitBook operations."""
    
    if operation == "read_page":
        url = params.get('url')
        
        if not url:
            return {"error": "URL required for read_page operation"}
        
        # Ensure it's a proper GitBook URL
        if 'gitbook.io' not in url and 'gitbook.com' not in url:
            return {"error": "URL must be a GitBook documentation URL"}
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; GitBook-Reader-Tool/1.0)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Extract content
            result = extract_gitbook_content(response.text, url)
            
            return {
                "success": True,
                "data": result,
                "status_code": response.status_code
            }
            
        except requests.RequestException as e:
            return {"error": f"Failed to fetch GitBook page: {str(e)}"}
        except Exception as e:
            return {"error": f"Failed to parse GitBook content: {str(e)}"}
    
    elif operation == "search_page":
        url = params.get('url')
        query = params.get('query')
        
        if not url or not query:
            return {"error": "URL and query required for search_page operation"}
        
        # First read the page
        read_result = run("read_page", url=url)
        
        if "error" in read_result:
            return read_result
        
        # Search in the content
        content = read_result["data"]["content"]
        matches = search_in_content(content, query)
        
        return {
            "success": True,
            "query": query,
            "url": url,
            "title": read_result["data"]["title"],
            "matches_count": len(matches),
            "matches": matches,
            "word_count": read_result["data"]["word_count"]
        }
    
    elif operation == "get_page_structure":
        url = params.get('url')
        
        if not url:
            return {"error": "URL required for get_page_structure operation"}
        
        # Read the page and return only structural information
        read_result = run("read_page", url=url)
        
        if "error" in read_result:
            return read_result
        
        data = read_result["data"]
        
        return {
            "success": True,
            "title": data["title"],
            "headings": data["headings"],
            "links": data["links"],
            "word_count": data["word_count"],
            "url": data["url"]
        }
    
    elif operation == "extract_links":
        url = params.get('url')
        internal_only = params.get('internal_only', True)
        
        if not url:
            return {"error": "URL required for extract_links operation"}
        
        # Read the page
        read_result = run("read_page", url=url)
        
        if "error" in read_result:
            return read_result
        
        links = read_result["data"]["links"]
        
        if internal_only:
            links = [link for link in links if link["internal"]]
        
        return {
            "success": True,
            "url": url,
            "links_count": len(links),
            "links": links
        }
    
    else:
        return {"error": f"Unknown operation: {operation}"}


def spec() -> Dict[str, Any]:
    """Return the MCP function specification."""
    
    return {
        "type": "function",
        "function": {
            "name": "gitbook",
            "description": "Read and search public GitBook documentations without authentication token. Access public docs, extract content, search within pages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": [
                            "read_page",
                            "search_page", 
                            "get_page_structure",
                            "extract_links"
                        ],
                        "description": "GitBook operation: read_page (get full content), search_page (search within page), get_page_structure (get headings/links), extract_links (get navigation links)"
                    },
                    "url": {
                        "type": "string",
                        "description": "GitBook page URL (e.g., https://docs.example.gitbook.io/page-name)"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query for search_page operation"
                    },
                    "internal_only": {
                        "type": "boolean",
                        "description": "For extract_links: return only internal links within the same GitBook (default: true)"
                    }
                },
                "required": ["operation", "url"],
                "additionalProperties": False
            }
        }
    }