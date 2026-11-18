"""One bounded HTTP statement per call; intended only for tiny course queries.

No transaction/session negotiation, spooling or transparent POST retries.
"""
import time
from .settings import TRINO_URL, TRINO_USER


def query(statement, *, timeout_seconds=150, session=None):
    import requests

    owned = session is None
    session = session or requests.Session()
    if owned:
        session.trust_env = False
    deadline = time.monotonic() + timeout_seconds
    next_uri = None
    rows = []

    def check(response):
        if response.status_code != 200:
            raise RuntimeError(f"Trino HTTP status {response.status_code}")
        return response.json()

    try:
        page = check(session.post(
            TRINO_URL + "/v1/statement", data=statement.encode("utf-8"),
            headers={"X-Trino-User": TRINO_USER,
                     "X-Trino-Source": "airflow-ecommerce-course",
                     "X-Trino-Session": "task_concurrency=1,query_max_run_time=2m,query_max_memory=128MB"},
            timeout=min(20, timeout_seconds),
        ))
        while True:
            next_uri = page.get("nextUri")
            if "error" in page:
                # Do not log external connector error messages or response bodies.
                raise RuntimeError("Trino statement failed; inspect its query in the Trino UI")
            rows.extend(page.get("data", []))
            if not next_uri:
                return rows
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Trino course query exceeded its deadline")
            page = check(session.get(next_uri, timeout=min(20, remaining)))
    finally:
        if next_uri:
            try:
                session.delete(next_uri, timeout=5)
            except requests.RequestException:
                pass  # Server-side two-minute limit also bounds unfinished work.
        if owned:
            session.close()
