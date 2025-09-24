from typing import Dict, List, Any
from .base import GitHubClient


class UsersClient(GitHubClient):
    """GitHub Users API client."""
    
    def get_user(self, username: str) -> Dict[str, Any]:
        """Get public information about a user."""
        return self.get(f"/users/{username}")
    
    def get_authenticated_user(self) -> Dict[str, Any]:
        """Get the authenticated user."""
        return self.get("/user")
    
    def update_authenticated_user(self, name: str = None, email: str = None, bio: str = None, company: str = None, location: str = None, blog: str = None) -> Dict[str, Any]:
        """Update the authenticated user."""
        data = {}
        if name is not None:
            data["name"] = name
        if email is not None:
            data["email"] = email
        if bio is not None:
            data["bio"] = bio
        if company is not None:
            data["company"] = company
        if location is not None:
            data["location"] = location
        if blog is not None:
            data["blog"] = blog
        
        return self.patch("/user", json=data)
    
    def list_followers(self, username: str) -> List[Dict[str, Any]]:
        """List followers of a user."""
        return self.get_all_pages(f"/users/{username}/followers")
    
    def list_following(self, username: str) -> List[Dict[str, Any]]:
        """List users that a user is following."""
        return self.get_all_pages(f"/users/{username}/following")
    
    def check_following(self, username: str, target_user: str) -> bool:
        """Check if a user follows another user."""
        try:
            self.get(f"/users/{username}/following/{target_user}")
            return True
        except:
            return False
    
    def follow_user(self, username: str) -> bool:
        """Follow a user."""
        response = self._request('PUT', f"/user/following/{username}")
        return response.status_code == 204
    
    def unfollow_user(self, username: str) -> bool:
        """Unfollow a user."""
        return self.delete(f"/user/following/{username}")
    
    def list_starred_repos(self, username: str) -> List[Dict[str, Any]]:
        """List repositories starred by a user."""
        return self.get_all_pages(f"/users/{username}/starred")
    
    def list_user_orgs(self, username: str) -> List[Dict[str, Any]]:
        """List organizations for a user."""
        return self.get_all_pages(f"/users/{username}/orgs")
    
    def list_user_events(self, username: str) -> List[Dict[str, Any]]:
        """List public events for a user."""
        return self.get_all_pages(f"/users/{username}/events/public")
    
    def search_users(self, query: str, sort: str = None, order: str = "desc") -> Dict[str, Any]:
        """Search for users."""
        params = {"q": query}
        if sort:
            params["sort"] = sort
        params["order"] = order
        return self.get("/search/users", params=params)