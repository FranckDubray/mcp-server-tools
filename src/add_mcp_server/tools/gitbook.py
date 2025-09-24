"""
Enhanced GitBook Tool - Smart discovery and global search
Automatically discover all pages and search across entire documentation
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Set
import re
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree
import time


def clean_text(text: str) -> str:
    """Clean and format text from HTML."""
    if not text:
        return ""
    
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    # Remove common GitBook navigation elements
    text = re.sub(r'Table of contents|On this page|Previous|Next', '', text, flags=re.IGNORECASE)
    
    return text


def discover_sitemap(base_url: str) -> List[str]:
    """Try to discover pages via sitemap.xml."""
    sitemap_urls = [
        f"{base_url.rstrip('/')}/sitemap.xml",
        f"{base_url.rstrip('/')}/sitemap_index.xml"
    ]
    
    pages = []
    
    for sitemap_url in sitemap_urls:
        try:
            response = requests.get(sitemap_url, timeout=10)
            if response.status_code == 200:
                # Parse XML sitemap
                root = ElementTree.fromstring(response.content)
                
                # Handle namespaces
                namespaces = {
                    '': 'http://www.sitemaps.org/schemas/sitemap/0.9'
                }
                
                # Extract URLs
                for url_elem in root.findall('.//url', namespaces) or root.findall('.//url'):
                    loc_elem = url_elem.find('loc', namespaces) or url_elem.find('loc')
                    if loc_elem is not None and loc_elem.text:
                        pages.append(loc_elem.text.strip())
                
                if pages:
                    break  # Found sitemap, stop trying others
                    
        except Exception as e:
            continue
    
    return pages


def discover_navigation(base_url: str) -> List[str]:
    """Discover pages by crawling navigation from base URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; GitBook-Enhanced-Tool/1.0)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        
        response = requests.get(base_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract all internal links
        pages = set()
        base_domain = f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}"
        
        for link in soup.select('a[href]'):
            href = link.get('href')
            if href:
                full_url = urljoin(base_url, href)
                parsed = urlparse(full_url)
                
                # Only include internal links that look like GitBook pages
                if (parsed.netloc == urlparse(base_url).netloc and 
                    not href.startswith('#') and 
                    not href.startswith('mailto:') and
                    not href.endswith('.pdf') and
                    not href.endswith('.zip') and
                    '/api/' not in href):
                    pages.add(full_url)
        
        return list(pages)
        
    except Exception as e:
        return []


def extract_page_content(url: str) -> Dict[str, Any]:
    """Extract content from a single GitBook page."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; GitBook-Enhanced-Tool/1.0)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title = ""
        for selector in ['h1', '[data-testid="page-title"]', 'title']:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = clean_text(title_elem.get_text())
                break
        
        # Extract main content
        content = ""
        content_selectors = [
            '[data-testid="page-content"]',
            '.page-body',
            'main article',
            '.content',
            'main'
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # Remove navigation and TOC elements
                for nav in content_elem.select('nav, .toc, .table-of-contents, .pagination'):
                    nav.decompose()
                
                content = clean_text(content_elem.get_text())
                break
        
        # If no structured content found, get body text
        if not content:
            for element in soup(['script', 'style', 'nav', 'header', 'footer']):
                element.decompose()
            content = clean_text(soup.get_text())
        
        # Extract headings for structure
        headings = []
        for heading in soup.select('h1, h2, h3, h4, h5, h6'):
            headings.append({
                "level": int(heading.name[1]),
                "text": clean_text(heading.get_text())
            })
        
        return {
            "url": url,
            "title": title,
            "content": content,
            "headings": headings,
            "word_count": len(content.split()) if content else 0,
            "success": True
        }
        
    except Exception as e:
        return {
            "url": url,
            "error": str(e),
            "success": False
        }


def search_in_pages(pages_data: List[Dict], query: str, max_results: int = 10) -> List[Dict]:
    """Search for query across all pages and return ranked results."""
    if not query:
        return []
    
    query_lower = query.lower()
    results = []
    
    for page in pages_data:
        if not page.get("success") or not page.get("content"):
            continue
        
        content = page["content"]
        title = page.get("title", "")
        
        # Calculate relevance score
        score = 0
        
        # Title matches are very important
        if query_lower in title.lower():
            score += 10
        
        # Count occurrences in content
        content_lower = content.lower()
        occurrences = content_lower.count(query_lower)
        score += occurrences
        
        # Bonus for exact phrase matches
        if query_lower in content_lower:
            score += 5
        
        if score > 0:
            # Extract snippets with context
            snippets = []
            words = content.split()
            
            for i, word in enumerate(words):
                if query_lower in word.lower():
                    start = max(0, i - 10)
                    end = min(len(words), i + 10)
                    snippet = ' '.join(words[start:end])
                    
                    # Highlight the match
                    snippet_highlighted = re.sub(
                        f'({re.escape(query)})', 
                        f'**{query}**', 
                        snippet, 
                        flags=re.IGNORECASE
                    )
                    
                    snippets.append(f"...{snippet_highlighted}...")
                    
                    if len(snippets) >= 3:  # Max 3 snippets per page
                        break
            
            results.append({
                "url": page["url"],
                "title": title,
                "score": score,
                "occurrences": occurrences,
                "snippets": snippets,
                "word_count": page.get("word_count", 0)
            })
    
    # Sort by score (relevance)
    results.sort(key=lambda x: x["score"], reverse=True)
    
    return results[:max_results]


def run(operation: str, **params) -> Dict[str, Any]:
    """Execute GitBook operations with enhanced discovery and search."""
    
    if operation == "discover_site":
        base_url = params.get('base_url')
        
        if not base_url:
            return {"error": "base_url required for discover_site operation"}
        
        # Try multiple discovery methods
        pages = []
        methods_used = []
        
        # Method 1: Sitemap
        sitemap_pages = discover_sitemap(base_url)
        if sitemap_pages:
            pages.extend(sitemap_pages)
            methods_used.append("sitemap")
        
        # Method 2: Navigation crawling
        nav_pages = discover_navigation(base_url)
        if nav_pages:
            # Merge and deduplicate
            pages_set = set(pages)
            new_pages = [p for p in nav_pages if p not in pages_set]
            pages.extend(new_pages)
            if new_pages:
                methods_used.append("navigation")
        
        # Remove duplicates and filter
        unique_pages = list(set(pages))
        
        # Filter to keep only relevant GitBook pages
        filtered_pages = []
        base_domain = urlparse(base_url).netloc
        
        for page_url in unique_pages:
            parsed = urlparse(page_url)
            if (parsed.netloc == base_domain and 
                not page_url.endswith('.xml') and
                not page_url.endswith('.json')):
                filtered_pages.append(page_url)
        
        return {
            "success": True,
            "base_url": base_url,
            "pages_found": len(filtered_pages),
            "discovery_methods": methods_used,
            "pages": filtered_pages[:50],  # Limit to first 50 for display
            "total_discovered": len(unique_pages)
        }
    
    elif operation == "search_site":
        base_url = params.get('base_url')
        query = params.get('query')
        max_results = params.get('max_results', 10)
        max_pages = params.get('max_pages', 20)
        
        if not base_url or not query:
            return {"error": "base_url and query required for search_site operation"}
        
        # First discover pages
        discovery = run("discover_site", base_url=base_url)
        if "error" in discovery:
            return discovery
        
        pages_to_search = discovery["pages"][:max_pages]
        
        # Extract content from each page
        pages_data = []
        processed = 0
        
        for page_url in pages_to_search:
            page_data = extract_page_content(page_url)
            pages_data.append(page_data)
            processed += 1
            
            # Add small delay to be respectful
            time.sleep(0.1)
        
        # Search across all pages
        search_results = search_in_pages(pages_data, query, max_results)
        
        return {
            "success": True,
            "query": query,
            "base_url": base_url,
            "pages_searched": processed,
            "results_found": len(search_results),
            "results": search_results
        }
    
    elif operation == "read_page":
        # Keep the original functionality
        url = params.get('url')
        
        if not url:
            return {"error": "URL required for read_page operation"}
        
        result = extract_page_content(url)
        return result
    
    else:
        return {"error": f"Unknown operation: {operation}. Available: discover_site, search_site, read_page"}


def spec() -> Dict[str, Any]:
    """Return the enhanced MCP function specification."""
    
    return {
        "type": "function",
        "function": {
            "name": "gitbook",
            "description": "Enhanced GitBook tool with smart discovery and global search. Automatically find all pages in a GitBook site and search across entire documentation without knowing specific URLs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": [
                            "discover_site",
                            "search_site",
                            "read_page"
                        ],
                        "description": "Operation: discover_site (find all pages), search_site (search across entire documentation), read_page (read specific page)"
                    },
                    "base_url": {
                        "type": "string",
                        "description": "Base URL of GitBook site (e.g., https://docs.example.gitbook.io)"
                    },
                    "url": {
                        "type": "string",
                        "description": "Specific page URL for read_page operation"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query for search_site operation"
                    },
                    "max_results": {
                        "type": "number",
                        "description": "Maximum search results to return (default: 10)"
                    },
                    "max_pages": {
                        "type": "number",
                        "description": "Maximum pages to search through (default: 20)"
                    }
                },
                "required": ["operation"],
                "additionalProperties": False
            }
        }
    }