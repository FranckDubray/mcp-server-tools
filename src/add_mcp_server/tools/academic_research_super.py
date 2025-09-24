"""
🎓 Academic Research Tool Super - Version multi-sources optimisée

Sources intégrées: PubMed, arXiv, HAL, CrossRef
Réponses compactes pour préserver le contexte LLM
"""

import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import re
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from collections import Counter


@dataclass
class Author:
    name: str
    affiliation: str = ""


@dataclass
class ResearchResult:
    title: str
    authors: List[Author]
    abstract: str
    doi: str
    url: str
    publication_date: str
    journal: str
    source: str
    citations_count: int = 0
    full_text_url: str = ""


class AcademicResearchSuper:
    """Recherche académique multi-sources optimisée"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Academic-Research-Super/1.0 (Python; Educational Use)'
        }
        self.last_request = {}
    
    def _rate_limit(self, source: str, delay: float = 1.0):
        """Rate limiting par source"""
        now = time.time()
        if source in self.last_request:
            elapsed = now - self.last_request[source]
            if elapsed < delay:
                time.sleep(delay - elapsed)
        self.last_request[source] = time.time()
    
    def search_papers(self, query: str, source: str = "all", max_results: int = 5, 
                     author: Optional[str] = None, year_start: Optional[int] = None,
                     year_end: Optional[int] = None) -> List[ResearchResult]:
        """Recherche multi-sources avec limite réduite"""
        results_list = []
        
        # Limite stricte pour éviter le flood
        max_results = min(max_results, 10)  # Max 10 résultats
        
        if source == "all":
            sources = ["arxiv", "pubmed", "hal"]
            per_source = max(max_results // len(sources), 1)
        else:
            sources = [source]
            per_source = max_results
        
        for src in sources:
            try:
                if src == "arxiv":
                    results = self.search_arxiv(query, author, per_source)
                elif src == "pubmed":
                    results = self.search_pubmed(query, author, year_start, year_end, per_source)
                elif src == "hal":
                    results = self.search_hal(query, author, year_start, year_end, per_source)
                elif src == "crossref":
                    results = self.search_crossref(query, author, per_source)
                else:
                    continue
                
                if src in ["arxiv", "crossref"] and (year_start or year_end):
                    results = self._filter_by_year(results, year_start, year_end)
                
                results_list.extend(results)
                
            except Exception as e:
                print(f"Erreur {src}: {e}")
                continue
        
        return results_list[:max_results]
    
    def search_arxiv(self, query: str, author: Optional[str] = None, max_results: int = 5) -> List[ResearchResult]:
        """Recherche arXiv optimisée"""
        try:
            self._rate_limit("arxiv", 2.0)
            
            arxiv_query = f"all:{query}"
            if author:
                arxiv_query += f" AND au:{author}"
            
            encoded_query = urllib.parse.quote(arxiv_query)
            url = f"http://export.arxiv.org/api/query?search_query={encoded_query}&start=0&max_results={max_results}&sortBy=relevance"
            
            req = urllib.request.Request(url, headers=self.headers)
            
            with urllib.request.urlopen(req, timeout=15) as response:
                xml_str = response.read().decode('utf-8')
                return self._parse_arxiv_xml(xml_str)
                
        except Exception as e:
            print(f"Erreur arXiv: {e}")
            return []
    
    def search_pubmed(self, query: str, author: Optional[str] = None,
                     year_start: Optional[int] = None, year_end: Optional[int] = None,
                     max_results: int = 5) -> List[ResearchResult]:
        """Recherche PubMed optimisée"""
        try:
            self._rate_limit("pubmed", 1.0)
            
            pubmed_query = query
            if author:
                pubmed_query += f" AND {author}[author]"
            if year_start and year_end:
                pubmed_query += f" AND {year_start}:{year_end}[pdat]"
            
            encoded_query = urllib.parse.quote(pubmed_query)
            search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={encoded_query}&retmax={max_results}&retmode=json"
            
            req = urllib.request.Request(search_url, headers=self.headers)
            
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode('utf-8'))
                ids = data.get('esearchresult', {}).get('idlist', [])
            
            if not ids:
                return []
            
            self._rate_limit("pubmed", 1.0)
            fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={','.join(ids)}&retmode=xml"
            
            req = urllib.request.Request(fetch_url, headers=self.headers)
            
            with urllib.request.urlopen(req, timeout=15) as response:
                xml_str = response.read().decode('utf-8')
                return self._parse_pubmed_xml(xml_str)
                
        except Exception as e:
            print(f"Erreur PubMed: {e}")
            return []
    
    def search_hal(self, query: str, author: Optional[str] = None,
                  year_start: Optional[int] = None, year_end: Optional[int] = None,
                  max_results: int = 5) -> List[ResearchResult]:
        """Recherche HAL optimisée"""
        try:
            self._rate_limit("hal", 1.5)
            
            params = {
                'q': query,
                'rows': min(max_results, 10),
                'fl': 'title_s,authFullName_s,abstract_s,uri_s,producedDate_s,journalTitle_s,doiId_s',
                'sort': 'producedDate_tdate desc',
                'wt': 'json'
            }
            
            filters = []
            if author:
                filters.append(f'authFullName_t:"{author}"')
            if year_start:
                filters.append(f'producedDate_tdate:[{year_start}-01-01T00:00:00Z TO *]')
            if year_end:
                filters.append(f'producedDate_tdate:[* TO {year_end}-12-31T23:59:59Z]')
            
            if filters:
                params['fq'] = ' AND '.join(filters)
            
            query_string = urllib.parse.urlencode(params)
            url = f"https://api.archives-ouvertes.fr/search/?{query_string}"
            
            req = urllib.request.Request(url, headers=self.headers)
            
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode('utf-8'))
                return self._parse_hal_json(data)
                
        except Exception as e:
            print(f"Erreur HAL: {e}")
            return []
    
    def search_crossref(self, query: str, author: Optional[str] = None, max_results: int = 5) -> List[ResearchResult]:
        """Recherche CrossRef optimisée"""
        try:
            self._rate_limit("crossref", 1.0)
            
            params = {
                'query': query,
                'rows': min(max_results, 10),
                'sort': 'relevance'
            }
            
            if author:
                params['query.author'] = author
            
            query_string = urllib.parse.urlencode(params)
            url = f"https://api.crossref.org/works?{query_string}"
            
            crossref_headers = {
                'User-Agent': 'Academic-Research-Super/1.0 (mailto:research@example.edu)',
                'Accept': 'application/json'
            }
            
            req = urllib.request.Request(url, headers=crossref_headers)
            
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode('utf-8'))
                return self._parse_crossref_json(data)
                
        except Exception as e:
            print(f"Erreur CrossRef: {e}")
            return []
    
    def get_paper_by_id(self, paper_id: str) -> Optional[ResearchResult]:
        """Récupère un paper par ID"""
        try:
            if re.match(r'^\d+$', paper_id):  # PMID
                results = self.search_pubmed(f"{paper_id}[pmid]", max_results=1)
                return results[0] if results else None
            elif re.match(r'^\d{4}\.\d+', paper_id):  # arXiv ID
                return self._get_arxiv_by_id(paper_id)
            elif '/' in paper_id:  # DOI
                results = self.search_crossref(f'doi:"{paper_id}"', max_results=1)
                return results[0] if results else None
            else:
                return None
        except:
            return None
    
    def search_by_author(self, author_name: str, source: str = "all", max_results: int = 5) -> List[ResearchResult]:
        """Recherche par auteur avec limite stricte"""
        max_results = min(max_results, 15)  # Max 15 pour les auteurs
        return self.search_papers("", source=source, max_results=max_results, author=author_name)
    
    def get_author_stats(self, author_name: str) -> Dict[str, Any]:
        """Statistiques d'auteur compactes"""
        papers = self.search_by_author(author_name, source="all", max_results=10)  # Limite à 10
        
        if not papers:
            return {"error": f"Aucune publication trouvée pour {author_name}"}
        
        sources = Counter([p.source for p in papers])
        journals = [p.journal for p in papers if p.journal]
        years = [int(p.publication_date) for p in papers if p.publication_date.isdigit()]
        total_citations = sum(getattr(p, 'citations_count', 0) for p in papers)
        
        return {
            "author": author_name,
            "total_papers": len(papers),
            "sources_found": dict(sources),
            "total_citations": total_citations,
            "years_active": f"{min(years) if years else 'N/A'} - {max(years) if years else 'N/A'}",
            "top_journals": [j for j, c in Counter(journals).most_common(3)],  # Max 3
            "sample_papers": [  # 3 exemples max
                {"title": p.title[:50] + "..." if len(p.title) > 50 else p.title, 
                 "year": p.publication_date, "source": p.source}
                for p in papers[:3]
            ]
        }
    
    def _filter_by_year(self, results: List[ResearchResult], year_start: Optional[int], year_end: Optional[int]) -> List[ResearchResult]:
        """Filtre par année"""
        if not year_start and not year_end:
            return results
        
        filtered = []
        for result in results:
            if result.publication_date and result.publication_date.isdigit():
                year = int(result.publication_date)
                if year_start and year < year_start:
                    continue
                if year_end and year > year_end:
                    continue
            filtered.append(result)
        
        return filtered
    
    def _get_arxiv_by_id(self, arxiv_id: str) -> Optional[ResearchResult]:
        """Récupère par arXiv ID"""
        try:
            self._rate_limit("arxiv", 2.0)
            url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}&max_results=1"
            req = urllib.request.Request(url, headers=self.headers)
            
            with urllib.request.urlopen(req, timeout=15) as response:
                xml_str = response.read().decode('utf-8')
                results = self._parse_arxiv_xml(xml_str)
                return results[0] if results else None
        except:
            return None
    
    def _parse_arxiv_xml(self, xml_str: str) -> List[ResearchResult]:
        """Parse XML arXiv optimisé"""
        results = []
        
        try:
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            root = ET.fromstring(xml_str)
            
            for entry in root.findall('atom:entry', ns):
                try:
                    title_elem = entry.find('atom:title', ns)
                    title = title_elem.text.strip() if title_elem is not None else ""
                    
                    authors = []
                    for author in entry.findall('atom:author', ns)[:3]:  # Max 3 auteurs
                        name_elem = author.find('atom:name', ns)
                        if name_elem is not None:
                            authors.append(Author(name=name_elem.text))
                    
                    summary_elem = entry.find('atom:summary', ns)
                    abstract = summary_elem.text.strip() if summary_elem is not None else ""
                    abstract = abstract[:200] + "..." if len(abstract) > 200 else abstract  # Tronqué
                    
                    id_elem = entry.find('atom:id', ns)
                    url = id_elem.text if id_elem is not None else ""
                    pdf_url = url.replace('/abs/', '/pdf/') + '.pdf' if url else ""
                    
                    published_elem = entry.find('atom:published', ns)
                    pub_date = published_elem.text[:4] if published_elem is not None else ""
                    
                    results.append(ResearchResult(
                        title=title,
                        authors=authors,
                        abstract=abstract,
                        doi="",
                        url=url,
                        publication_date=pub_date,
                        journal="arXiv",
                        source="arXiv",
                        full_text_url=pdf_url
                    ))
                    
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"Erreur parsing arXiv: {e}")
        
        return results
    
    def _parse_pubmed_xml(self, xml_str: str) -> List[ResearchResult]:
        """Parse XML PubMed optimisé"""
        results = []
        
        try:
            root = ET.fromstring(xml_str)
            
            for article in root.findall('.//PubmedArticle'):
                try:
                    title_elem = article.find('.//ArticleTitle')
                    title = title_elem.text if title_elem is not None else ""
                    
                    pmid_elem = article.find('.//PMID')
                    pmid = pmid_elem.text if pmid_elem is not None else ""
                    
                    authors = []
                    for author in article.findall('.//Author')[:3]:  # Max 3 auteurs
                        lastname = author.find('LastName')
                        forename = author.find('ForeName')
                        if forename is not None and lastname is not None:
                            name = f"{forename.text} {lastname.text}"
                            affiliation = ""
                            affil_elem = author.find('AffiliationInfo/Affiliation')
                            if affil_elem is not None:
                                affiliation = affil_elem.text[:50]  # Tronqué
                            authors.append(Author(name=name, affiliation=affiliation))
                    
                    abstract_parts = []
                    for abstract_elem in article.findall('.//AbstractText'):
                        if abstract_elem.text:
                            abstract_parts.append(abstract_elem.text)
                    abstract = " ".join(abstract_parts)
                    abstract = abstract[:200] + "..." if len(abstract) > 200 else abstract  # Tronqué
                    
                    journal_elem = article.find('.//Journal/Title')
                    journal = journal_elem.text if journal_elem is not None else ""
                    
                    doi_elem = article.find('.//ELocationID[@EIdType="doi"]')
                    doi = doi_elem.text if doi_elem is not None else ""
                    
                    date_elem = article.find('.//PubDate/Year')
                    pub_date = date_elem.text if date_elem is not None else ""
                    
                    url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""
                    
                    results.append(ResearchResult(
                        title=title,
                        authors=authors,
                        abstract=abstract,
                        doi=doi,
                        url=url,
                        publication_date=pub_date,
                        journal=journal,
                        source="PubMed"
                    ))
                    
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"Erreur parsing PubMed: {e}")
        
        return results
    
    def _parse_hal_json(self, Dict) -> List[ResearchResult]:
        """Parse JSON HAL optimisé"""
        results = []
        
        try:
            docs = data.get('response', {}).get('docs', [])
            
            for doc in docs:
                try:
                    title = doc.get('title_s', [''])[0] if doc.get('title_s') else ""
                    
                    authors = []
                    author_names = doc.get('authFullName_s', [])
                    for name in author_names[:3]:  # Max 3 auteurs
                        authors.append(Author(name=name))
                    
                    abstract = doc.get('abstract_s', [''])[0] if doc.get('abstract_s') else ""
                    abstract = abstract[:200] + "..." if len(abstract) > 200 else abstract  # Tronqué
                    
                    url = doc.get('uri_s', '')
                    date = doc.get('producedDate_s', '')
                    pub_date = date[:4] if date else ""
                    journal = doc.get('journalTitle_s', ['HAL'])[0] if doc.get('journalTitle_s') else "HAL"
                    doi = doc.get('doiId_s', '')
                    
                    results.append(ResearchResult(
                        title=title,
                        authors=authors,
                        abstract=abstract,
                        doi=doi,
                        url=url,
                        publication_date=pub_date,
                        journal=journal,
                        source="HAL"
                    ))
                    
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"Erreur parsing HAL: {e}")
        
        return results
    
    def _parse_crossref_json(self, data: Dict) -> List[ResearchResult]:
        """Parse JSON CrossRef optimisé"""
        results = []
        
        try:
            works = data.get('message', {}).get('items', [])
            
            for work in works:
                try:
                    titles = work.get('title', [])
                    title = titles[0] if titles else ""
                    
                    authors = []
                    for author_data in work.get('author', [])[:3]:  # Max 3 auteurs
                        given = author_data.get('given', '')
                        family = author_data.get('family', '')
                        if family:
                            name = f"{given} {family}".strip()
                            authors.append(Author(name=name))
                    
                    abstract = work.get('abstract', '')
                    abstract = abstract[:200] + "..." if len(abstract) > 200 else abstract
                    
                    doi = work.get('DOI', '')
                    url = work.get('URL', f"https://doi.org/{doi}" if doi else '')
                    
                    container_titles = work.get('container-title', [])
                    journal = container_titles[0] if container_titles else ""
                    
                    pub_date = ""
                    date_parts = work.get('published-print', {}).get('date-parts')
                    if not date_parts:
                        date_parts = work.get('published-online', {}).get('date-parts')
                    if date_parts and date_parts[0]:
                        pub_date = str(date_parts[0][0])
                    
                    citations_count = work.get('is-referenced-by-count', 0)
                    
                    results.append(ResearchResult(
                        title=title,
                        authors=authors,
                        abstract=abstract,
                        doi=doi,
                        url=url,
                        publication_date=pub_date,
                        journal=journal,
                        source="CrossRef",
                        citations_count=citations_count
                    ))
                    
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"Erreur parsing CrossRef: {e}")
        
        return results


# Instance globale
_tool = AcademicResearchSuper()

def run(**params) -> Dict[str, Any]:
    """Point d'entrée MCP optimisé"""
    try:
        operation = params.get('operation', 'search_papers')
        
        if operation == "search_papers":
            query = params.get('query', '')
            source = params.get('source', 'all')
            max_results = min(params.get('max_results', 5), 10)  # Limite stricte
            author = params.get('author')
            year_start = params.get('year_start')
            year_end = params.get('year_end')
            
            if not query and not author:
                return {"success": False, "error": "Query ou author requis"}
            
            results_list = _tool.search_papers(query, source, max_results, author, year_start, year_end)
            
            # Réponse compacte
            return {
                "success": True,
                "query": query,
                "source": source,
                "total_results": len(results_list),
                "sources_found": list(set([r.source for r in results_list])),
                "results": [
                    {
                        "title": r.title[:80] + "..." if len(r.title) > 80 else r.title,  # Titre tronqué
                        "authors": [a.name for a in r.authors[:2]],  # Max 2 auteurs
                        "abstract": r.abstract,  # Déjà tronqué dans le parsing
                        "year": r.publication_date,
                        "journal": r.journal,
                        "source": r.source,
                        "url": r.url,
                        "doi": r.doi
                    }
                    for r in results_list
                ]
            }
        
        elif operation == "get_paper_details":
            paper_id = params.get('paper_id', '')
            
            if not paper_id:
                return {"success": False, "error": "paper_id requis"}
            
            paper = _tool.get_paper_by_id(paper_id)
            
            if not paper:
                return {"success": False, "error": f"Paper {paper_id} non trouvé"}
            
            return {
                "success": True,
                "paper": {
                    "title": paper.title,
                    "authors": [a.name for a in paper.authors],
                    "abstract": paper.abstract,
                    "year": paper.publication_date,
                    "journal": paper.journal,
                    "source": paper.source,
                    "url": paper.url,
                    "doi": paper.doi
                }
            }
        
        elif operation == "search_by_author":
            author_name = params.get('author_name', '')
            source = params.get('source', 'all')
            max_results = min(params.get('max_results', 5), 10)  # Limite stricte
            
            if not author_name:
                return {"success": False, "error": "author_name requis"}
            
            papers = _tool.search_by_author(author_name, source, max_results)
            
            return {
                "success": True,
                "author": author_name,
                "total_papers": len(papers),
                "sources_found": list(set([p.source for p in papers])),
                "papers": [
                    {
                        "title": p.title[:60] + "..." if len(p.title) > 60 else p.title,
                        "year": p.publication_date,
                        "source": p.source,
                        "url": p.url
                    }
                    for p in papers
                ]
            }
        
        elif operation == "get_author_stats":
            author_name = params.get('author_name', '')
            
            if not author_name:
                return {"success": False, "error": "author_name requis"}
            
            stats = _tool.get_author_stats(author_name)
            
            return {
                "success": True,
                **stats
            }
        
        else:
            return {
                "success": False, 
                "error": f"Opération '{operation}' non supportée",
                "supported_operations": ["search_papers", "get_paper_details", "search_by_author", "get_author_stats"]
            }
            
    except Exception as e:
        return {"success": False, "error": str(e)}


def spec() -> Dict[str, Any]:
    """Spécification OpenAI Functions Super"""
    return {
        "type": "function", 
        "function": {
            "name": "academic_research_super",
            "description": "🎓 Recherche académique Super multi-sources - PubMed, arXiv, HAL (France), CrossRef avec analytics avancées",
            "parameters": {
                "type": "object",
                "required": ["operation"],
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["search_papers", "get_paper_details", "search_by_author", "get_author_stats"],
                        "description": "Opération : recherche, détails paper, recherche auteur, stats auteur"
                    },
                    "query": {
                        "type": "string", 
                        "description": "Termes de recherche (pour search_papers)"
                    },
                    "source": {
                        "type": "string",
                        "enum": ["all", "arxiv", "pubmed", "hal", "crossref"],
                        "description": "Source - all: toutes, arxiv: physique/math/CS, pubmed: médecine, hal: archives françaises, crossref: DOI/citations"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Nombre max de résultats (défaut: 5, max: 10)"
                    },
                    "author": {
                        "type": "string",
                        "description": "Nom d'auteur pour filtrer/rechercher"
                    },
                    "author_name": {
                        "type": "string",
                        "description": "Nom d'auteur (pour search_by_author, get_author_stats)"
                    },
                    "paper_id": {
                        "type": "string",
                        "description": "ID du paper - PMID, arXiv ID, ou DOI (pour get_paper_details)"
                    },
                    "year_start": {
                        "type": "integer",
                        "description": "Année de début (ex: 2020)"
                    },
                    "year_end": {
                        "type": "integer", 
                        "description": "Année de fin (ex: 2024)"
                    }
                },
                "additionalProperties": False
            }
        }
    }


if __name__ == "__main__":
    result = run(operation="search_papers", query="machine learning", max_results=3)
    print(json.dumps(result, indent=2, ensure_ascii=False))