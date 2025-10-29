# app.py
import streamlit as st
import pandas as pd
from services.gitlab_service import GitLabService
from services.jira_service import JiraService
from nlp.nlp_score import compute_jira_score
from utils.constants import DEFAULT_ASSIGNEES
import os
from dotenv import load_dotenv

load_dotenv()  # load .env if present

st.set_page_config(page_title="GitLab → Jira NLP Dashboard", layout="wide")

st.title("🔗 GitLab → Jira NLP Dashboard")

with st.sidebar:
    st.header("Connection Settings")
    gitlab_base = st.text_input("GitLab base URL", os.getenv("GITLAB_BASE", "https://gitlab.com"))
    project = st.text_input("Project (path or ID)", os.getenv("GITLAB_PROJECT", "group/project"))
    gitlab_token = st.text_input("GitLab Private Token", os.getenv("GITLAB_TOKEN", ""), type="password")

    st.markdown("---")
    st.subheader("Jira Settings")
    jira_base = st.text_input("Jira base URL", os.getenv("JIRA_BASE", "https://yourcompany.atlassian.net"))
    jira_user = st.text_input("Jira user (email)", os.getenv("JIRA_USER", ""))
    jira_token = st.text_input("Jira API token/password", os.getenv("JIRA_TOKEN", ""), type="password")

    st.markdown("---")
    st.subheader("Assignees")
    # Pre-fill three required users
    assignees = st.multiselect("Assignees to scan (select 1..3)", DEFAULT_ASSIGNEES, default=DEFAULT_ASSIGNEES)

    st.markdown("---")
    st.write("Notes:")
    st.write("- Make sure tokens have required scopes (GitLab: api, Jira: read)")
    fetch_btn = st.button("Fetch MRs & Score")

def validate_inputs():
    missing = []
    if not gitlab_base: missing.append("GitLab base")
    if not project: missing.append("Project")
    if not gitlab_token: missing.append("GitLab token")
    if not jira_base: missing.append("Jira base")
    if not jira_user: missing.append("Jira user")
    if not jira_token: missing.append("Jira token")
    if not assignees: missing.append("Assignees")
    return missing

if fetch_btn:
    missing = validate_inputs()
    if missing:
        st.error(f"Missing: {', '.join(missing)}")
    else:
        git = GitLabService(gitlab_base, gitlab_token)
        jira = JiraService(jira_base, jira_user, jira_token)

        final_rows = []
        progress = st.progress(0)
        total_assignees = len(assignees)
        current = 0

        for assignee in assignees:
            st.write(f"### Scanning MRs assigned to **{assignee}**")
            try:
                mrs = git.fetch_mrs_assigned_to(project, assignee)
            except Exception as e:
                st.error(f"Error fetching MRs for {assignee}: {e}")
                continue

            if not mrs:
                st.info(f"No MRs found for {assignee}")
            for mr in mrs:
                mr_iid = mr.get("iid")
                mr_title = mr.get("title")
                mr_url = mr.get("web_url") or mr.get("url")
                try:
                    commits = git.fetch_mr_commits(project, mr_iid)
                except Exception as e:
                    st.warning(f"Could not fetch commits for MR {mr_iid}: {e}")
                    commits = []

                jira_map = git.extract_jira_keys_from_commits(commits)
                if not jira_map:
                    # still add MR row with no jira
                    final_rows.append({
                        "assignee": assignee,
                        "mr_iid": mr_iid,
                        "mr_title": mr_title,
                        "mr_url": mr_url,
                        "jira_key": None,
                        "jira_summary": None,
                        "score": None,
                        "reason": "no_jira_in_commits"
                    })
                else:
                    for key, commits_list in jira_map.items():
                        jira_issue = jira.fetch_issue(key)
                        score_obj = compute_jira_score(jira_issue)
                        summary = None
                        if jira_issue and not jira_issue.get("error"):
                            summary = (jira_issue.get("fields") or {}).get("summary")
                        final_rows.append({
                            "assignee": assignee,
                            "mr_iid": mr_iid,
                            "mr_title": mr_title,
                            "mr_url": mr_url,
                            "jira_key": key,
                            "jira_summary": summary,
                            "score": score_obj.get("score"),
                            "reason": score_obj.get("reason")
                        })

            current += 1
            progress.progress(int(current/total_assignees*100))

        # Present results
        if final_rows:
            df = pd.DataFrame(final_rows)
            st.subheader("Results")
            st.dataframe(df, use_container_width=True)

            st.markdown("### Score distribution")
            if df["score"].dropna().shape[0] > 0:
                st.bar_chart(df.dropna(subset=["score"])["score"])
            else:
                st.info("No scored Jira issues found.")

            # CSV download
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download CSV", csv, "gitlab_jira_scores.csv", "text/csv")
        else:
            st.info("No MRs or Jira issues found for the selected assignees.")
