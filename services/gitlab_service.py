# services/gitlab_service.py
import requests
import urllib.parse
from utils.helper import paginate_get
from utils.constants import JIRA_KEY_RE
import re

class GitLabService:
    def __init__(self, gitlab_base, token):
        """
        gitlab_base: e.g. https://gitlab.com or https://gitlab.company.com
        token: personal access token (PRIVATE-TOKEN) with api scope
        """
        self.base = gitlab_base.rstrip('/')
        self.headers = {"PRIVATE-TOKEN": token} if token else {}
        self.jira_re = re.compile(JIRA_KEY_RE)

    def project_api_base(self, project_path_or_id):
        # GitLab API accepts encoded project path in /projects/:id
        encoded = urllib.parse.quote_plus(project_path_or_id)
        return f"{self.base}/api/v4/projects/{encoded}"

    def fetch_mrs_assigned_to(self, project_path_or_id, assignee_username):
        """
        Returns list of merge requests assigned to assignee_username.
        """
        url = f"{self.project_api_base(project_path_or_id)}/merge_requests"
        params = {"state": "all", "assignee_username": assignee_username}
        return paginate_get(url, headers=self.headers, params=params)

    def fetch_mr_commits(self, project_path_or_id, mr_iid):
        """
        Fetch commits for a given MR IID
        """
        url = f"{self.project_api_base(project_path_or_id)}/merge_requests/{mr_iid}/commits"
        r = requests.get(url, headers=self.headers, timeout=30)
        r.raise_for_status()
        return r.json()

    def extract_jira_keys_from_commits(self, commits):
        """
        commits: list of commit objects from GitLab API
        returns dict: {jira_key: [ {sha, message}, ... ], ...}
        """
        keys = {}
        for c in commits:
            sha = c.get("id") or c.get("sha")
            message = c.get("message", "")
            for match in self.jira_re.findall(message):
                keys.setdefault(match, []).append({"sha": sha, "message": message})
        return keys
