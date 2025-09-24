from typing import Dict, List, Any, Optional
from .base import GitHubClient


class IssuesClient(GitHubClient):
    """GitHub Issues API client."""
    
    def list_issues(self, owner: str, repo: str, state: str = "open", labels: str = None, assignee: str = None, sort: str = "created", direction: str = "desc") -> List[Dict[str, Any]]:
        """List repository issues."""
        params = {
            "state": state,
            "sort": sort,
            "direction": direction
        }
        if labels:
            params["labels"] = labels
        if assignee:
            params["assignee"] = assignee
            
        return self.get_all_pages(f"/repos/{owner}/{repo}/issues", params=params)
    
    def get_issue(self, owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
        """Get a specific issue."""
        return self.get(f"/repos/{owner}/{repo}/issues/{issue_number}")
    
    def create_issue(self, owner: str, repo: str, title: str, body: str = "", assignees: List[str] = None, labels: List[str] = None) -> Dict[str, Any]:
        """Create a new issue."""
        data = {
            "title": title,
            "body": body
        }
        if assignees:
            data["assignees"] = assignees
        if labels:
            data["labels"] = labels
            
        return self.post(f"/repos/{owner}/{repo}/issues", json=data)
    
    def update_issue(self, owner: str, repo: str, issue_number: int, title: str = None, body: str = None, state: str = None, assignees: List[str] = None, labels: List[str] = None) -> Dict[str, Any]:
        """Update an existing issue."""
        data = {}
        if title is not None:
            data["title"] = title
        if body is not None:
            data["body"] = body
        if state is not None:
            data["state"] = state
        if assignees is not None:
            data["assignees"] = assignees
        if labels is not None:
            data["labels"] = labels
            
        return self.patch(f"/repos/{owner}/{repo}/issues/{issue_number}", json=data)
    
    def close_issue(self, owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
        """Close an issue."""
        return self.update_issue(owner, repo, issue_number, state="closed")
    
    def reopen_issue(self, owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
        """Reopen an issue."""
        return self.update_issue(owner, repo, issue_number, state="open")
    
    def list_issue_comments(self, owner: str, repo: str, issue_number: int) -> List[Dict[str, Any]]:
        """List comments for an issue."""
        return self.get_all_pages(f"/repos/{owner}/{repo}/issues/{issue_number}/comments")
    
    def get_issue_comment(self, owner: str, repo: str, comment_id: int) -> Dict[str, Any]:
        """Get a specific issue comment."""
        return self.get(f"/repos/{owner}/{repo}/issues/comments/{comment_id}")
    
    def create_issue_comment(self, owner: str, repo: str, issue_number: int, body: str) -> Dict[str, Any]:
        """Create a comment on an issue."""
        data = {"body": body}
        return self.post(f"/repos/{owner}/{repo}/issues/{issue_number}/comments", json=data)
    
    def update_issue_comment(self, owner: str, repo: str, comment_id: int, body: str) -> Dict[str, Any]:
        """Update an issue comment."""
        data = {"body": body}
        return self.patch(f"/repos/{owner}/{repo}/issues/comments/{comment_id}", json=data)
    
    def delete_issue_comment(self, owner: str, repo: str, comment_id: int) -> bool:
        """Delete an issue comment."""
        return self.delete(f"/repos/{owner}/{repo}/issues/comments/{comment_id}")
    
    def list_labels(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """List repository labels."""
        return self.get_all_pages(f"/repos/{owner}/{repo}/labels")
    
    def get_label(self, owner: str, repo: str, name: str) -> Dict[str, Any]:
        """Get a specific label."""
        return self.get(f"/repos/{owner}/{repo}/labels/{name}")
    
    def create_label(self, owner: str, repo: str, name: str, color: str, description: str = "") -> Dict[str, Any]:
        """Create a new label."""
        data = {
            "name": name,
            "color": color.lstrip('#'),  # Remove # if present
            "description": description
        }
        return self.post(f"/repos/{owner}/{repo}/labels", json=data)
    
    def update_label(self, owner: str, repo: str, current_name: str, name: str = None, color: str = None, description: str = None) -> Dict[str, Any]:
        """Update a label."""
        data = {}
        if name is not None:
            data["name"] = name
        if color is not None:
            data["color"] = color.lstrip('#')
        if description is not None:
            data["description"] = description
            
        return self.patch(f"/repos/{owner}/{repo}/labels/{current_name}", json=data)
    
    def delete_label(self, owner: str, repo: str, name: str) -> bool:
        """Delete a label."""
        return self.delete(f"/repos/{owner}/{repo}/labels/{name}")
    
    def add_labels_to_issue(self, owner: str, repo: str, issue_number: int, labels: List[str]) -> List[Dict[str, Any]]:
        """Add labels to an issue."""
        data = {"labels": labels}
        return self.post(f"/repos/{owner}/{repo}/issues/{issue_number}/labels", json=data)
    
    def remove_label_from_issue(self, owner: str, repo: str, issue_number: int, name: str) -> bool:
        """Remove a label from an issue."""
        return self.delete(f"/repos/{owner}/{repo}/issues/{issue_number}/labels/{name}")
    
    def search_issues(self, query: str, sort: str = None, order: str = "desc") -> Dict[str, Any]:
        """Search for issues and pull requests."""
        params = {"q": query}
        if sort:
            params["sort"] = sort
        params["order"] = order
        return self.get("/search/issues", params=params)