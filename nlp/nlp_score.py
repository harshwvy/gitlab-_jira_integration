# nlp/nlp_score.py
import math
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

PRIORITY_WEIGHTS = {
    # common Jira priority names
    "Blocker": 1.0, "Highest":1.0, "Critical":1.0,
    "High": 0.9, "Major": 0.85,
    "Medium": 0.6, "Normal": 0.6,
    "Low": 0.3, "Minor": 0.3
}

def compute_jira_score(jira_issue):
    """
    Input: jira_issue (dict) from Jira API or None
    Output: dict {score: float, reason: str, sentiment: float, priority: str}
    Score range 0..100 (higher = more severe/urgent)
    """
    if not jira_issue:
        return {"score": None, "reason": "no_issue"}

    if jira_issue.get("error"):
        return {"score": None, "reason": f"jira_error:{jira_issue.get('status_code')}"}

    fields = jira_issue.get("fields", {})
    summary = fields.get("summary") or ""
    # description may be complex (dict) — try to string cast safely
    description = fields.get("description") or ""
    if isinstance(description, dict):
        # Jira Cloud sometimes returns Atlassian Document Format; fallback to str()
        description_text = str(description)
    else:
        description_text = description

    combined = f"{summary}\n{description_text}"
    sentiment = analyzer.polarity_scores(combined).get("compound", 0.0)

    # sentiment base: negative -> higher severity
    base_sent = (1 - sentiment) / 2 * 50  # 0..50

    priority_field = fields.get("priority") or {}
    priority_name = priority_field.get("name", "Medium")
    pr_weight = PRIORITY_WEIGHTS.get(priority_name, 0.6)

    # length score
    desc_len = len(combined)
    length_score = math.tanh(desc_len / 1000) * 20  # up to 20 points

    # labels
    labels = fields.get("labels") or []
    label_boost = 0
    for l in labels:
        ll = l.lower()
        if "urgent" in ll or "block" in ll or "critical" in ll or "security" in ll:
            label_boost += 10

    raw = (base_sent + length_score + label_boost) * pr_weight
    final = max(0.0, min(100.0, round(raw, 2)))
    reason = f"sent_base={round(base_sent,2)} len={round(length_score,2)} labels={label_boost} pwt={pr_weight}"
    return {"score": final, "reason": reason, "sentiment": sentiment, "priority": priority_name}
