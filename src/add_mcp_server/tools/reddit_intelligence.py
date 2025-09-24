"""
Reddit Intelligence Tool - Advanced Reddit analysis and insights
Search, analyze sentiment, find experts, track trends across Reddit
"""

import requests
from typing import Dict, Any, List, Optional
import re
from datetime import datetime, timedelta
import time
from collections import Counter
import json


class RedditIntelligence:
    """Reddit intelligence and analysis tool"""
    
    def __init__(self):
        self.base_url = "https://www.reddit.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; Reddit-Intelligence-Tool/1.0)',
            'Accept': 'application/json, text/html'
        }
    
    def clean_text(self, text: str) -> str:
        """Clean Reddit text content"""
        if not text:
            return ""
        
        # Remove Reddit markdown
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # Links
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*(.*?)\*', r'\1', text)  # Italic
        text = re.sub(r'~~(.*?)~~', r'\1', text)  # Strikethrough
        text = re.sub(r'^&gt;(.+)', r'> \1', text, flags=re.MULTILINE)  # Quotes
        
        # Clean extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        return text
    
    def get_json_data(self, url: str) -> Optional[Dict]:
        """Get JSON data from Reddit API"""
        try:
            # Add .json to URL if not present
            if not url.endswith('.json'):
                url += '.json'
            
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            return None
    
    def search_subreddit(self, subreddit: str, query: str = "", sort: str = "hot", 
                        limit: int = 25, time_filter: str = "all") -> Dict[str, Any]:
        """Search within a specific subreddit"""
        try:
            if query:
                # Search with query
                url = f"{self.base_url}/r/{subreddit}/search.json"
                params = {
                    'q': query,
                    'restrict_sr': 'on',
                    'sort': sort,
                    'limit': limit,
                    't': time_filter
                }
                
                response = requests.get(url, headers=self.headers, params=params, timeout=15)
            else:
                # Get subreddit posts
                url = f"{self.base_url}/r/{subreddit}/{sort}.json"
                params = {
                    'limit': limit,
                    't': time_filter
                }
                
                response = requests.get(url, headers=self.headers, params=params, timeout=15)
            
            response.raise_for_status()
            data = response.json()
            
            if 'data' not in data or 'children' not in data['data']:
                return {"error": "Invalid response format", "subreddit": subreddit}
            
            posts = []
            for post in data['data']['children']:
                post_data = post['data']
                
                posts.append({
                    'id': post_data.get('id', ''),
                    'title': self.clean_text(post_data.get('title', '')),
                    'author': post_data.get('author', '[deleted]'),
                    'score': post_data.get('score', 0),
                    'upvote_ratio': post_data.get('upvote_ratio', 0),
                    'num_comments': post_data.get('num_comments', 0),
                    'created_utc': post_data.get('created_utc', 0),
                    'url': post_data.get('url', ''),
                    'permalink': f"{self.base_url}{post_data.get('permalink', '')}",
                    'selftext': self.clean_text(post_data.get('selftext', '')),
                    'flair': post_data.get('link_flair_text', ''),
                    'is_video': post_data.get('is_video', False),
                    'over_18': post_data.get('over_18', False),
                    'subreddit': post_data.get('subreddit', '')
                })
            
            return {
                'success': True,
                'subreddit': subreddit,
                'query': query,
                'sort': sort,
                'posts_found': len(posts),
                'posts': posts
            }
            
        except Exception as e:
            return {
                'success': False,
                'subreddit': subreddit,
                'error': str(e)
            }
    
    def get_post_comments(self, subreddit: str, post_id: str, limit: int = 50) -> Dict[str, Any]:
        """Get comments from a specific post"""
        try:
            url = f"{self.base_url}/r/{subreddit}/comments/{post_id}.json"
            params = {'limit': limit}
            
            response = requests.get(url, headers=self.headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if len(data) < 2:
                return {"error": "Invalid post or no comments", "post_id": post_id}
            
            # First element is the post, second is comments
            post_info = data[0]['data']['children'][0]['data']
            comments_data = data[1]['data']['children']
            
            def extract_comment(comment_data, depth=0):
                if 'data' not in comment_data:
                    return None
                
                c_data = comment_data['data']
                
                comment = {
                    'id': c_data.get('id', ''),
                    'author': c_data.get('author', '[deleted]'),
                    'body': self.clean_text(c_data.get('body', '')),
                    'score': c_data.get('score', 0),
                    'created_utc': c_data.get('created_utc', 0),
                    'depth': depth,
                    'replies': []
                }
                
                # Get replies
                if 'replies' in c_data and c_data['replies'] and depth < 3:  # Limit depth
                    if isinstance(c_data['replies'], dict) and 'data' in c_data['replies']:
                        for reply in c_data['replies']['data'].get('children', []):
                            reply_comment = extract_comment(reply, depth + 1)
                            if reply_comment:
                                comment['replies'].append(reply_comment)
                
                return comment
            
            comments = []
            for comment_data in comments_data[:limit]:
                comment = extract_comment(comment_data)
                if comment and comment['body']:  # Skip deleted/empty comments
                    comments.append(comment)
            
            return {
                'success': True,
                'post_id': post_id,
                'post_title': self.clean_text(post_info.get('title', '')),
                'post_author': post_info.get('author', ''),
                'post_score': post_info.get('score', 0),
                'comments_found': len(comments),
                'comments': comments
            }
            
        except Exception as e:
            return {
                'success': False,
                'post_id': post_id,
                'error': str(e)
            }
    
    def analyze_sentiment(self, texts: List[str]) -> Dict[str, Any]:
        """Basic sentiment analysis of text list"""
        if not texts:
            return {"error": "No texts provided for sentiment analysis"}
        
        # Simple keyword-based sentiment analysis
        positive_words = [
            'good', 'great', 'excellent', 'amazing', 'awesome', 'love', 'like', 
            'best', 'perfect', 'wonderful', 'fantastic', 'brilliant', 'outstanding',
            'helpful', 'useful', 'easy', 'simple', 'clear', 'works', 'solved'
        ]
        
        negative_words = [
            'bad', 'terrible', 'awful', 'horrible', 'hate', 'dislike', 'worst',
            'broken', 'useless', 'confusing', 'difficult', 'hard', 'problem',
            'issue', 'bug', 'error', 'fails', 'doesnt work', "doesn't work"
        ]
        
        sentiments = []
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        for text in texts:
            text_lower = text.lower()
            
            pos_score = sum(1 for word in positive_words if word in text_lower)
            neg_score = sum(1 for word in negative_words if word in text_lower)
            
            if pos_score > neg_score:
                sentiment = 'positive'
                positive_count += 1
            elif neg_score > pos_score:
                sentiment = 'negative'
                negative_count += 1
            else:
                sentiment = 'neutral'
                neutral_count += 1
            
            sentiments.append({
                'text': text[:100] + '...' if len(text) > 100 else text,
                'sentiment': sentiment,
                'positive_score': pos_score,
                'negative_score': neg_score
            })
        
        total = len(texts)
        return {
            'success': True,
            'total_analyzed': total,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'positive_percentage': round((positive_count / total) * 100, 1),
            'negative_percentage': round((negative_count / total) * 100, 1),
            'neutral_percentage': round((neutral_count / total) * 100, 1),
            'overall_sentiment': 'positive' if positive_count > negative_count else 'negative' if negative_count > positive_count else 'neutral',
            'detailed_results': sentiments[:10]  # Show first 10 detailed results
        }
    
    def find_trending_topics(self, subreddit: str = "all", time_filter: str = "day", limit: int = 50) -> Dict[str, Any]:
        """Find trending topics in a subreddit"""
        try:
            posts_result = self.search_subreddit(subreddit, "", "hot", limit, time_filter)
            
            if not posts_result.get('success'):
                return posts_result
            
            posts = posts_result['posts']
            
            # Extract keywords from titles
            all_words = []
            for post in posts:
                title = post['title'].lower()
                # Remove common words and extract meaningful terms
                words = re.findall(r'\b[a-zA-Z]{3,}\b', title)
                
                # Filter out common words
                stop_words = {
                    'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'she', 'use', 'your', 'about', 'would', 'there', 'could', 'other', 'after', 'first', 'never', 'these', 'think', 'where', 'being', 'every', 'great', 'might', 'shall', 'still', 'those', 'under', 'while', 'this', 'that', 'with', 'have', 'from', 'they', 'know', 'want', 'been', 'good', 'much', 'some', 'time', 'very', 'when', 'come', 'here', 'just', 'like', 'long', 'make', 'many', 'over', 'such', 'take', 'than', 'them', 'well', 'were', 'what'
                }
                
                filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
                all_words.extend(filtered_words)
            
            # Count word frequency
            word_counts = Counter(all_words)
            trending_words = word_counts.most_common(20)
            
            # Analyze post metrics
            total_score = sum(post['score'] for post in posts)
            avg_score = total_score / len(posts) if posts else 0
            total_comments = sum(post['num_comments'] for post in posts)
            
            # Find top posts
            top_posts = sorted(posts, key=lambda x: x['score'], reverse=True)[:5]
            
            return {
                'success': True,
                'subreddit': subreddit,
                'time_filter': time_filter,
                'posts_analyzed': len(posts),
                'trending_keywords': [{'word': word, 'frequency': count} for word, count in trending_words],
                'metrics': {
                    'total_score': total_score,
                    'average_score': round(avg_score, 1),
                    'total_comments': total_comments,
                    'average_comments': round(total_comments / len(posts), 1) if posts else 0
                },
                'top_posts': [{
                    'title': post['title'],
                    'score': post['score'],
                    'comments': post['num_comments'],
                    'author': post['author'],
                    'permalink': post['permalink']
                } for post in top_posts]
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def find_experts(self, subreddit: str, topic: str = "", min_karma_threshold: int = 1000) -> Dict[str, Any]:
        """Find expert users in a subreddit based on activity and karma"""
        try:
            # Search for topic or get general posts
            posts_result = self.search_subreddit(subreddit, topic, "top", 50, "month")
            
            if not posts_result.get('success'):
                return posts_result
            
            posts = posts_result['posts']
            
            # Analyze authors
            author_stats = {}
            
            for post in posts:
                author = post['author']
                if author == '[deleted]':
                    continue
                
                if author not in author_stats:
                    author_stats[author] = {
                        'posts': 0,
                        'total_score': 0,
                        'total_comments': 0,
                        'avg_score': 0,
                        'posts_list': []
                    }
                
                author_stats[author]['posts'] += 1
                author_stats[author]['total_score'] += post['score']
                author_stats[author]['total_comments'] += post['num_comments']
                author_stats[author]['posts_list'].append({
                    'title': post['title'],
                    'score': post['score'],
                    'comments': post['num_comments']
                })
            
            # Calculate averages and filter experts
            experts = []
            for author, stats in author_stats.items():
                if stats['posts'] >= 2:  # At least 2 posts
                    stats['avg_score'] = stats['total_score'] / stats['posts']
                    
                    # Score expert based on multiple factors
                    expert_score = (
                        stats['avg_score'] * 0.4 +
                        stats['posts'] * 10 +
                        stats['total_comments'] * 0.1
                    )
                    
                    experts.append({
                        'username': author,
                        'expert_score': round(expert_score, 1),
                        'posts_count': stats['posts'],
                        'avg_post_score': round(stats['avg_score'], 1),
                        'total_karma_earned': stats['total_score'],
                        'engagement_generated': stats['total_comments'],
                        'top_posts': sorted(stats['posts_list'], key=lambda x: x['score'], reverse=True)[:3]
                    })
            
            # Sort by expert score
            experts.sort(key=lambda x: x['expert_score'], reverse=True)
            
            return {
                'success': True,
                'subreddit': subreddit,
                'topic': topic or 'general',
                'posts_analyzed': len(posts),
                'experts_found': len(experts),
                'experts': experts[:10]  # Top 10 experts
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def multi_subreddit_search(self, subreddits: List[str], query: str, limit_per_sub: int = 10) -> Dict[str, Any]:
        """Search across multiple subreddits"""
        all_results = []
        subreddit_stats = []
        
        for subreddit in subreddits:
            result = self.search_subreddit(subreddit, query, "hot", limit_per_sub)
            
            if result.get('success'):
                posts = result['posts']
                all_results.extend(posts)
                
                subreddit_stats.append({
                    'subreddit': subreddit,
                    'posts_found': len(posts),
                    'avg_score': round(sum(p['score'] for p in posts) / len(posts), 1) if posts else 0,
                    'total_comments': sum(p['num_comments'] for p in posts)
                })
            else:
                subreddit_stats.append({
                    'subreddit': subreddit,
                    'error': result.get('error', 'Unknown error')
                })
            
            # Small delay between requests
            time.sleep(0.5)
        
        # Sort all results by score
        all_results.sort(key=lambda x: x['score'], reverse=True)
        
        return {
            'success': True,
            'query': query,
            'subreddits_searched': len(subreddits),
            'total_posts_found': len(all_results),
            'results': all_results,
            'subreddit_breakdown': subreddit_stats
        }


def run(operation: str, **params) -> Dict[str, Any]:
    """Execute Reddit intelligence operations"""
    reddit = RedditIntelligence()
    
    if operation == "search_subreddit":
        subreddit = params.get('subreddit')
        query = params.get('query', '')
        sort = params.get('sort', 'hot')
        limit = params.get('limit', 25)
        time_filter = params.get('time_filter', 'all')
        
        if not subreddit:
            return {"error": "subreddit required for search_subreddit operation"}
        
        return reddit.search_subreddit(subreddit, query, sort, limit, time_filter)
    
    elif operation == "get_comments":
        subreddit = params.get('subreddit')
        post_id = params.get('post_id')
        limit = params.get('limit', 50)
        
        if not subreddit or not post_id:
            return {"error": "subreddit and post_id required for get_comments operation"}
        
        return reddit.get_post_comments(subreddit, post_id, limit)
    
    elif operation == "analyze_sentiment":
        subreddit = params.get('subreddit')
        query = params.get('query', '')
        limit = params.get('limit', 25)
        
        if not subreddit:
            return {"error": "subreddit required for analyze_sentiment operation"}
        
        # Get posts first
        posts_result = reddit.search_subreddit(subreddit, query, "hot", limit)
        
        if not posts_result.get('success'):
            return posts_result
        
        # Extract texts for sentiment analysis
        texts = []
        for post in posts_result['posts']:
            texts.append(post['title'])
            if post['selftext']:
                texts.append(post['selftext'])
        
        sentiment_result = reddit.analyze_sentiment(texts)
        sentiment_result['subreddit'] = subreddit
        sentiment_result['query'] = query
        sentiment_result['posts_analyzed'] = len(posts_result['posts'])
        
        return sentiment_result
    
    elif operation == "find_trending":
        subreddit = params.get('subreddit', 'all')
        time_filter = params.get('time_filter', 'day')
        limit = params.get('limit', 50)
        
        return reddit.find_trending_topics(subreddit, time_filter, limit)
    
    elif operation == "find_experts":
        subreddit = params.get('subreddit')
        topic = params.get('topic', '')
        min_karma = params.get('min_karma_threshold', 1000)
        
        if not subreddit:
            return {"error": "subreddit required for find_experts operation"}
        
        return reddit.find_experts(subreddit, topic, min_karma)
    
    elif operation == "multi_search":
        subreddits = params.get('subreddits', [])
        query = params.get('query')
        limit_per_sub = params.get('limit_per_sub', 10)
        
        if not subreddits or not query:
            return {"error": "subreddits and query required for multi_search operation"}
        
        return reddit.multi_subreddit_search(subreddits, query, limit_per_sub)
    
    else:
        return {
            "error": f"Unknown operation: {operation}. Available: search_subreddit, get_comments, analyze_sentiment, find_trending, find_experts, multi_search"
        }


def spec() -> Dict[str, Any]:
    """Return the MCP function specification for Reddit Intelligence"""
    
    return {
        "type": "function",
        "function": {
            "name": "reddit_intelligence",
            "description": "Advanced Reddit analysis tool. Search subreddits, analyze sentiment, find experts, track trends, get post comments. Discover insights from Reddit discussions and community activity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": [
                            "search_subreddit",
                            "get_comments",
                            "analyze_sentiment",
                            "find_trending", 
                            "find_experts",
                            "multi_search"
                        ],
                        "description": "Operation: search_subreddit (search posts in subreddit), get_comments (get post comments), analyze_sentiment (sentiment analysis of posts), find_trending (trending topics), find_experts (find expert users), multi_search (search across multiple subreddits)"
                    },
                    "subreddit": {
                        "type": "string",
                        "description": "Subreddit name (without r/). Use 'all' for all subreddits"
                    },
                    "subreddits": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of subreddit names for multi_search operation"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query or topic"
                    },
                    "post_id": {
                        "type": "string", 
                        "description": "Reddit post ID for get_comments operation"
                    },
                    "sort": {
                        "type": "string",
                        "enum": ["hot", "new", "top", "rising"],
                        "description": "Sort order for posts (default: hot)"
                    },
                    "time_filter": {
                        "type": "string",
                        "enum": ["hour", "day", "week", "month", "year", "all"],
                        "description": "Time filter for posts (default: all)"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of results (default: 25)"
                    },
                    "limit_per_sub": {
                        "type": "number",
                        "description": "Results limit per subreddit for multi_search (default: 10)"
                    },
                    "topic": {
                        "type": "string",
                        "description": "Specific topic for find_experts operation"
                    },
                    "min_karma_threshold": {
                        "type": "number",
                        "description": "Minimum karma threshold for experts (default: 1000)"
                    }
                },
                "required": ["operation"],
                "additionalProperties": False
            }
        }
    }