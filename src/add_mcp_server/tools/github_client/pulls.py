from typing import Dict, List, Any, Optional
from .base import GitHubClient


class PullsClient(GitHubClient):
    """GitHub Pull Requests API client."""
    
    def list_pulls(self, owner: str, repo: str, state: str = "open", head: str = None, base: str = None, sort: str = "created", direction: str = "desc") -> List[Dict[str, Any]]:
        """List repository pull requests."""
        params = {
            "state": state,
            "sort": sort,
            "direction": direction
        }
        if head:
            params["head"] = head
        if base:
            params["base"] = base
            
        return self.get_all_pages(f"/repos/{owner}/{repo}/pulls", params=params)
    
    def get_pull(self, owner: str, repo: str, pull_number: int) -> Dict[str, Any]:
        """Get a specific pull request."""
        return self.get(f"/repos/{owner}/{repo}/pulls/{pull_number}")
    
    def create_pull(self, owner: str, repo: str, title: str, head: str, base: str, body: str = "", draft: bool = False) -> Dict[str, Any]:
        """Create a new pull request."""
        data = {
            "title": title,
            "head": head,
            "base": base,
            "body": body,
            "draft": draft
        }
        return self.post(f"/repos/{owner}/{repo}/pulls", json=data)
    
    def update_pull(self, owner: str, repo: str, pull_number: int, title: str = None, body: str = None, state: str = None, base: str = None) -> Dict[str, Any]:
        """Update a pull request."""
        data = {}
        if title is not None:
            data["title"] = title
        if body is not None:
            data["body"] = body
        if state is not None:
            data["state"] = state
        if base is not None:
            data["base"] = base
            
        return self.patch(f"/repos/{owner}/{repo}/pulls/{pull_number}", json=data)
    
    def close_pull(self, owner: str, repo: str, pull_number: int) -> Dict[str, Any]:
        """Close a pull request."""
        return self.update_pull(owner, repo, pull_number, state="closed")
    
    def reopen_pull(self, owner: str, repo: str, pull_number: int) -> Dict[str, Any]:
        """Reopen a pull request."""
        return self.update_pull(owner, repo, pull_number, state="open")
    
    def merge_pull(self, owner: str, repo: str, pull_number: int, commit_title: str = None, commit_message: str = None, merge_method: str = "merge") -> Dict[str, Any]:
        """Merge a pull request."""
        data = {"merge_method": merge_method}
        if commit_title:
            data["commit_title"] = commit_title
        if commit_message:
            data["commit_message"] = commit_message
            
        return self.post(f"/repos/{owner}/{repo}/pulls/{pull_number}/merge", json=data)
    
    def get_pull_commits(self, owner: str, repo: str, pull_number: int) -> List[Dict[str, Any]]:
        """List commits in a pull request."""
        return self.get_all_pages(f"/repos/{owner}/{repo}/pulls/{pull_number}/commits")
    
    def get_pull_files(self, owner: str, repo: str, pull_number: int) -> List[Dict[str, Any]]:
        """List files changed in a pull request."""
        return self.get_all_pages(f"/repos/{owner}/{repo}/pulls/{pull_number}/files")
    
    def check_pull_merged(self, owner: str, repo: str, pull_number: int) -> bool:
        """Check if a pull request has been merged."""
        try:
            self.get(f"/repos/{owner}/{repo}/pulls/{pull_number}/merge")
            return True
        except:
            return False
    
    def list_pull_reviews(self, owner: str, repo: str, pull_number: int) -> List[Dict[str, Any]]:
        """List reviews for a pull request."""
        return self.get_all_pages(f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews")
    
    def get_pull_review(self, owner: str, repo: str, pull_number: int, review_id: int) -> Dict[str, Any]:
        """Get a specific pull request review."""
        return self.get(f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}")
    
    def create_pull_review(self, owner: str, repo: str, pull_number: int, body: str = "", event: str = "COMMENT", comments: List[Dict] = None) -> Dict[str, Any]:
        """Create a pull request review."""
        data = {
            "body": body,
            "event": event  # APPROVE, REQUEST_CHANGES, COMMENT
        }
        if comments:
            data["comments"] = comments
            
        return self.post(f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews", json=data)
    
    def update_pull_review(self, owner: str, repo: str, pull_number: int, review_id: int, body: str) -> Dict[str, Any]:
        """Update a pull request review."""
        data = {"body": body}
        return self.patch(f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}", json=data)
    
    def submit_pull_review(self, owner: str, repo: str, pull_number: int, review_id: int, event: str, body: str = "") -> Dict[str, Any]:
        """Submit a pull request review."""
        data = {
            "event": event,  # APPROVE, REQUEST_CHANGES, COMMENT
            "body": body
        }
        return self.post(f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/events", json=data)
    
    def dismiss_pull_review(self, owner: str, repo: str, pull_number: int, review_id: int, message: str) -> Dict[str, Any]:
        """Dismiss a pull request review."""
        data = {"message": message}
        return self.patch(f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/dismissals", json=data)
    
    def list_review_comments(self, owner: str, repo: str, pull_number: int) -> List[Dict[str, Any]]:
        """List review comments for a pull request."""
        return self.get_all_pages(f"/repos/{owner}/{repo}/pulls/{pull_number}/comments")
    
    def get_review_comment(self, owner: str, repo: str, comment_id: int) -> Dict[str, Any]:
        """Get a specific review comment."""
        return self.get(f"/repos/{owner}/{repo}/pulls/comments/{comment_id}")
    
    def create_review_comment(self, owner: str, repo: str, pull_number: int, body: str, commit_id: str, path: str, position: int) -> Dict[str, Any]:
        """Create a review comment on a pull request."""
        data = {
            "body": body,
            "commit_id": commit_id,
            "path": path,
            "position": position
        }
        return self.post(f"/repos/{owner}/{repo}/pulls/{pull_number}/comments", json=data)
    
    def update_review_comment(self, owner: str, repo: str, comment_id: int, body: str) -> Dict[str, Any]:
        """Update a review comment."""
        data = {"body": body}
        return self.patch(f"/repos/{owner}/{repo}/pulls/comments/{comment_id}", json=data)
    
    def delete_review_comment(self, owner: str, repo: str, comment_id: int) -> bool:
        """Delete a review comment."""
        return self.delete(f"/repos/{owner}/{repo}/pulls/comments/{comment_id}")