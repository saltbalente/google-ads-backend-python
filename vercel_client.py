import os
import time
import requests
from typing import Optional, Dict, Any, List


class VercelClient:
    def __init__(self, token: Optional[str] = None, team_id: Optional[str] = None, project_id: Optional[str] = None):
        self.token = token or os.getenv("VERCEL_TOKEN", "")
        self.team_id = team_id or os.getenv("VERCEL_TEAM_ID", "")
        self.project_id = project_id or os.getenv("VERCEL_PROJECT_ID", "")
        self.base = "https://api.vercel.com"

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def _params(self):
        p = {}
        if self.team_id:
            p["teamId"] = self.team_id
        return p

    def list_deployments(self, limit: int = 20, search: Optional[Dict[str, Any]] = None):
        params = self._params()
        if self.project_id:
            params["projectId"] = self.project_id
        params["limit"] = limit
        if search:
            params.update(search)
        r = requests.get(f"{self.base}/v13/deployments", headers=self._headers(), params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def get_deployment(self, deployment_id: str):
        params = self._params()
        r = requests.get(f"{self.base}/v13/deployments/{deployment_id}", headers=self._headers(), params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def poll_ready(self, deployment_id: str, timeout_sec: int = 600, interval_sec: int = 5):
        start = time.time()
        while True:
            d = self.get_deployment(deployment_id)
            state = d.get("readyState") or d.get("state")
            if state in {"READY", "SUCCEEDED"}:
                return d
            if state in {"ERROR", "CANCELED"}:
                raise RuntimeError(f"Deployment failed: {state}")
            if time.time() - start > timeout_sec:
                raise TimeoutError("Deployment not ready in time")
            time.sleep(interval_sec)

    def create_alias(self, deployment_id: str, alias_domain: str):
        params = self._params()
        payload = {"deploymentId": deployment_id, "alias": alias_domain}
        r = requests.post(f"{self.base}/v2/aliases", headers=self._headers(), params=params, json=payload, timeout=30)
        if r.status_code == 409:
            return r.json()
        r.raise_for_status()
        return r.json()

    def create_deployment(self, github_repo: str, github_owner: str, branch: str = "main", project_name: Optional[str] = None) -> Dict[str, Any]:
        """Create a new Vercel deployment from a GitHub repository."""
        params = self._params()
        if self.project_id:
            params["projectId"] = self.project_id

        payload = {
            "name": project_name or f"{github_owner}-{github_repo}",
            "gitSource": {
                "type": "github",
                "repo": f"{github_owner}/{github_repo}",
                "ref": branch
            }
        }

        r = requests.post(f"{self.base}/v13/deployments", headers=self._headers(), params=params, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()

