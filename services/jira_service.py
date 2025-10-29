# services/jira_service.py
import requests
from requests.auth import HTTPBasicAuth
from functools import lru_cache

class JiraService:
    def __init__(self, jira_base, jira_user, jira_token):
        """
        jira_base: e.g. https://yourcompany.atlassian.net
        jira_user: email/username for Jira Cloud
        jira_token: API token/password
        """
        self.base = jira_base.rstrip('/')
        self.auth = HTTPBasicAuth(jira_user, jira_token)
        self.headers = {"Accept": "application/json"}

    @lru_cache(maxsize=1024)
    def fetch_issue(self, issue_key):
        url = f"{self.base}/rest/api/3/issue/{issue_key}"
        r = requests.get(url, headers=self.headers, auth=self.auth, timeout=30)
        if r.status_code == 200:
            return r.json()
        else:
            # return None or minimal structure to indicate failure
            return {"error": True, "status_code": r.status_code, "text": r.text}
