from typing import Dict, List, Any, Optional
from .base import GitHubClient


class OrgsClient(GitHubClient):
    """GitHub Organizations API client."""
    
    def get_org(self, org: str) -> Dict[str, Any]:
        """Get organization information."""
        return self.get(f"/orgs/{org}")
    
    def update_org(self, org: str, billing_email: str = None, company: str = None, email: str = None, twitter_username: str = None, location: str = None, name: str = None, description: str = None, blog: str = None) -> Dict[str, Any]:
        """Update an organization."""
        data = {}
        if billing_email is not None:
            data["billing_email"] = billing_email
        if company is not None:
            data["company"] = company
        if email is not None:
            data["email"] = email
        if twitter_username is not None:
            data["twitter_username"] = twitter_username
        if location is not None:
            data["location"] = location
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if blog is not None:
            data["blog"] = blog
            
        return self.patch(f"/orgs/{org}", json=data)
    
    def list_org_members(self, org: str, filter: str = "all", role: str = "all") -> List[Dict[str, Any]]:
        """List organization members."""
        params = {"filter": filter, "role": role}
        return self.get_all_pages(f"/orgs/{org}/members", params=params)
    
    def get_org_membership(self, org: str, username: str) -> Dict[str, Any]:
        """Get organization membership for a user."""
        return self.get(f"/orgs/{org}/memberships/{username}")
    
    def set_org_membership(self, org: str, username: str, role: str = "member") -> Dict[str, Any]:
        """Add or update organization membership."""
        data = {"role": role}
        return self.post(f"/orgs/{org}/memberships/{username}", json=data)
    
    def remove_org_member(self, org: str, username: str) -> bool:
        """Remove organization member."""
        return self.delete(f"/orgs/{org}/members/{username}")
    
    def list_org_teams(self, org: str) -> List[Dict[str, Any]]:
        """List organization teams."""
        return self.get_all_pages(f"/orgs/{org}/teams")
    
    def get_team(self, org: str, team_slug: str) -> Dict[str, Any]:
        """Get team information."""
        return self.get(f"/orgs/{org}/teams/{team_slug}")
    
    def create_team(self, org: str, name: str, description: str = "", privacy: str = "secret", permission: str = "pull") -> Dict[str, Any]:
        """Create a team."""
        data = {
            "name": name,
            "description": description,
            "privacy": privacy,  # secret, closed
            "permission": permission  # pull, push, admin
        }
        return self.post(f"/orgs/{org}/teams", json=data)
    
    def update_team(self, org: str, team_slug: str, name: str = None, description: str = None, privacy: str = None, permission: str = None) -> Dict[str, Any]:
        """Update a team."""
        data = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if privacy is not None:
            data["privacy"] = privacy
        if permission is not None:
            data["permission"] = permission
            
        return self.patch(f"/orgs/{org}/teams/{team_slug}", json=data)
    
    def delete_team(self, org: str, team_slug: str) -> bool:
        """Delete a team."""
        return self.delete(f"/orgs/{org}/teams/{team_slug}")
    
    def list_team_members(self, org: str, team_slug: str, role: str = "all") -> List[Dict[str, Any]]:
        """List team members."""
        params = {"role": role}
        return self.get_all_pages(f"/orgs/{org}/teams/{team_slug}/members", params=params)
    
    def get_team_membership(self, org: str, team_slug: str, username: str) -> Dict[str, Any]:
        """Get team membership for a user."""
        return self.get(f"/orgs/{org}/teams/{team_slug}/memberships/{username}")
    
    def add_team_member(self, org: str, team_slug: str, username: str, role: str = "member") -> Dict[str, Any]:
        """Add or update team membership."""
        data = {"role": role}
        return self.post(f"/orgs/{org}/teams/{team_slug}/memberships/{username}", json=data)
    
    def remove_team_member(self, org: str, team_slug: str, username: str) -> bool:
        """Remove team member."""
        return self.delete(f"/orgs/{org}/teams/{team_slug}/memberships/{username}")
    
    def list_team_repos(self, org: str, team_slug: str) -> List[Dict[str, Any]]:
        """List team repositories."""
        return self.get_all_pages(f"/orgs/{org}/teams/{team_slug}/repos")
    
    def check_team_repo_permission(self, org: str, team_slug: str, owner: str, repo: str) -> Dict[str, Any]:
        """Check team permissions for a repository."""
        return self.get(f"/orgs/{org}/teams/{team_slug}/repos/{owner}/{repo}")
    
    def add_team_repo(self, org: str, team_slug: str, owner: str, repo: str, permission: str = "pull") -> bool:
        """Add team repository."""
        data = {"permission": permission}  # pull, push, admin, maintain, triage
        response = self._request('PUT', f"/orgs/{org}/teams/{team_slug}/repos/{owner}/{repo}", json=data)
        return response.status_code == 204
    
    def remove_team_repo(self, org: str, team_slug: str, owner: str, repo: str) -> bool:
        """Remove team repository."""
        return self.delete(f"/orgs/{org}/teams/{team_slug}/repos/{owner}/{repo}")
    
    def list_org_hooks(self, org: str) -> List[Dict[str, Any]]:
        """List organization webhooks."""
        return self.get_all_pages(f"/orgs/{org}/hooks")
    
    def get_org_hook(self, org: str, hook_id: int) -> Dict[str, Any]:
        """Get organization webhook."""
        return self.get(f"/orgs/{org}/hooks/{hook_id}")
    
    def create_org_hook(self, org: str, name: str, config: Dict[str, Any], events: List[str] = None, active: bool = True) -> Dict[str, Any]:
        """Create organization webhook."""
        data = {
            "name": name,
            "config": config,
            "events": events or ["push"],
            "active": active
        }
        return self.post(f"/orgs/{org}/hooks", json=data)
    
    def update_org_hook(self, org: str, hook_id: int, config: Dict[str, Any] = None, events: List[str] = None, active: bool = None) -> Dict[str, Any]:
        """Update organization webhook."""
        data = {}
        if config is not None:
            data["config"] = config
        if events is not None:
            data["events"] = events
        if active is not None:
            data["active"] = active
            
        return self.patch(f"/orgs/{org}/hooks/{hook_id}", json=data)
    
    def delete_org_hook(self, org: str, hook_id: int) -> bool:
        """Delete organization webhook."""
        return self.delete(f"/orgs/{org}/hooks/{hook_id}")
    
    def ping_org_hook(self, org: str, hook_id: int) -> bool:
        """Ping organization webhook."""
        response = self._request('POST', f"/orgs/{org}/hooks/{hook_id}/pings")
        return response.status_code == 204