# utils/helper.py
import requests

def paginate_get(url, headers=None, params=None, per_page=100, timeout=30):
    """
    Simple paginator for GitLab API (page-based).
    Returns aggregated list of JSON items.
    """
    page = 1
    all_items = []
    while True:
        page_params = dict(params or {})
        page_params.update({"per_page": per_page, "page": page})
        r = requests.get(url, headers=headers, params=page_params, timeout=timeout)
        r.raise_for_status()
        items = r.json()
        if not items:
            break
        all_items.extend(items)
        # stop when fewer than requested per_page items returned
        if len(items) < per_page:
            break
        page += 1
    return all_items
