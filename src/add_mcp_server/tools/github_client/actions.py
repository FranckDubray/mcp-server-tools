from typing import Dict, List, Any, Optional
from .base import GitHubClient


class ActionsClient(GitHubClient):
    """GitHub Actions API client."""
    
    def list_workflows(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """List repository workflows."""
        return self.get(f"/repos/{owner}/{repo}/actions/workflows")["workflows"]
    
    def get_workflow(self, owner: str, repo: str, workflow_id: str) -> Dict[str, Any]:
        """Get a specific workflow."""
        return self.get(f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}")
    
    def list_workflow_runs(self, owner: str, repo: str, workflow_id: str = None, branch: str = None, event: str = None, status: str = None) -> List[Dict[str, Any]]:
        """List workflow runs."""
        if workflow_id:
            endpoint = f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs"
        else:
            endpoint = f"/repos/{owner}/{repo}/actions/runs"
            
        params = {}
        if branch:
            params["branch"] = branch
        if event:
            params["event"] = event
        if status:
            params["status"] = status
            
        result = self.get(endpoint, params=params)
        return result["workflow_runs"]
    
    def get_workflow_run(self, owner: str, repo: str, run_id: int) -> Dict[str, Any]:
        """Get a specific workflow run."""
        return self.get(f"/repos/{owner}/{repo}/actions/runs/{run_id}")
    
    def cancel_workflow_run(self, owner: str, repo: str, run_id: int) -> bool:
        """Cancel a workflow run."""
        response = self._request('POST', f"/repos/{owner}/{repo}/actions/runs/{run_id}/cancel")
        return response.status_code == 202
    
    def rerun_workflow(self, owner: str, repo: str, run_id: int) -> bool:
        """Rerun a workflow."""
        response = self._request('POST', f"/repos/{owner}/{repo}/actions/runs/{run_id}/rerun")
        return response.status_code == 201
    
    def rerun_failed_jobs(self, owner: str, repo: str, run_id: int) -> bool:
        """Rerun failed jobs in a workflow run."""
        response = self._request('POST', f"/repos/{owner}/{repo}/actions/runs/{run_id}/rerun-failed-jobs")
        return response.status_code == 201
    
    def list_workflow_run_jobs(self, owner: str, repo: str, run_id: int) -> List[Dict[str, Any]]:
        """List jobs for a workflow run."""
        result = self.get(f"/repos/{owner}/{repo}/actions/runs/{run_id}/jobs")
        return result["jobs"]
    
    def get_job(self, owner: str, repo: str, job_id: int) -> Dict[str, Any]:
        """Get a specific job."""
        return self.get(f"/repos/{owner}/{repo}/actions/jobs/{job_id}")
    
    def get_job_logs(self, owner: str, repo: str, job_id: int) -> str:
        """Get logs for a job."""
        response = self._request('GET', f"/repos/{owner}/{repo}/actions/jobs/{job_id}/logs")
        return response.text
    
    def get_workflow_run_logs(self, owner: str, repo: str, run_id: int) -> bytes:
        """Download workflow run logs (returns zip archive)."""
        response = self._request('GET', f"/repos/{owner}/{repo}/actions/runs/{run_id}/logs")
        return response.content
    
    def delete_workflow_run_logs(self, owner: str, repo: str, run_id: int) -> bool:
        """Delete workflow run logs."""
        return self.delete(f"/repos/{owner}/{repo}/actions/runs/{run_id}/logs")
    
    def list_repo_secrets(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """List repository secrets."""
        result = self.get(f"/repos/{owner}/{repo}/actions/secrets")
        return result["secrets"]
    
    def get_repo_secret(self, owner: str, repo: str, secret_name: str) -> Dict[str, Any]:
        """Get a repository secret."""
        return self.get(f"/repos/{owner}/{repo}/actions/secrets/{secret_name}")
    
    def create_or_update_repo_secret(self, owner: str, repo: str, secret_name: str, encrypted_value: str, key_id: str) -> Dict[str, Any]:
        """Create or update a repository secret."""
        data = {
            "encrypted_value": encrypted_value,
            "key_id": key_id
        }
        response = self._request('PUT', f"/repos/{owner}/{repo}/actions/secrets/{secret_name}", json=data)
        return response.status_code in [201, 204]
    
    def delete_repo_secret(self, owner: str, repo: str, secret_name: str) -> bool:
        """Delete a repository secret."""
        return self.delete(f"/repos/{owner}/{repo}/actions/secrets/{secret_name}")
    
    def get_repo_public_key(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository public key for secrets encryption."""
        return self.get(f"/repos/{owner}/{repo}/actions/secrets/public-key")
    
    def list_self_hosted_runners(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """List self-hosted runners for a repository."""
        result = self.get(f"/repos/{owner}/{repo}/actions/runners")
        return result["runners"]
    
    def get_self_hosted_runner(self, owner: str, repo: str, runner_id: int) -> Dict[str, Any]:
        """Get a self-hosted runner."""
        return self.get(f"/repos/{owner}/{repo}/actions/runners/{runner_id}")
    
    def delete_self_hosted_runner(self, owner: str, repo: str, runner_id: int) -> bool:
        """Delete a self-hosted runner."""
        return self.delete(f"/repos/{owner}/{repo}/actions/runners/{runner_id}")
    
    def create_registration_token(self, owner: str, repo: str) -> Dict[str, Any]:
        """Create a registration token for a self-hosted runner."""
        return self.post(f"/repos/{owner}/{repo}/actions/runners/registration-token")
    
    def create_remove_token(self, owner: str, repo: str) -> Dict[str, Any]:
        """Create a remove token for a self-hosted runner."""
        return self.post(f"/repos/{owner}/{repo}/actions/runners/remove-token")