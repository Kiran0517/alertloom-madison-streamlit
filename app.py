import streamlit as st
from typing import List, Dict

# -------------------------------
# Brand + page config
# -------------------------------
st.set_page_config(
    page_title="AlertLoom Telemetry Triage (Madison Demo)",
    layout="wide",
    page_icon="🧵",
)

# Basic CSS to match AlertLoom palette
ALERTLOOM_CSS = """
<style>
    .main {
        background-color: #0B1220;
        color: #F8FAFC;
    }
    [data-testid="stHeader"] {
        background: linear-gradient(90deg, #0B1220, #1F2A44);
    }
    .alert-card {
        background-color: #020617;
        border-radius: 16px;
        padding: 16px 20px;
        border: 1px solid #1F2937;
        margin-bottom: 14px;
    }
    .pill {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 8px;
    }
    .pill-high {
        background-color: #fecaca20;
        color: #fecaca;
        border: 1px solid #fecaca60;
    }
    .pill-medium {
        background-color: #fed7aa20;
        color: #fed7aa;
        border: 1px solid #fed7aa60;
    }
    .pill-low {
        background-color: #bbf7d020;
        color: #bbf7d0;
        border: 1px solid #bbf7d060;
    }
    .pill-category {
        background-color: #111827;
        color: #e5e7eb;
        border: 1px solid #1f2937;
    }
    .metric-label {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: .12em;
        color: #9CA3AF;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 600;
        color: #F9FAFB;
    }
    .severity-gate-label {
        font-weight: 600;
        color: #F97373;
    }
    a, a:visited {
        color: #00C2FF;
    }
</style>
"""
st.markdown(ALERTLOOM_CSS, unsafe_allow_html=True)

# -------------------------------
# Helper functions
# -------------------------------
def severity_from_line(line: str) -> str:
    text = line.upper()
    if any(tag in text for tag in ("[CRITICAL]", "CRITICAL", "[ERROR]", " ERROR", "PANIC", "FATAL")):
        return "High"
    if any(tag in text for tag in ("[WARNING]", "WARN", "DEGRADED")):
        return "Medium"
    return "Low"


def category_from_line(line: str) -> str:
    lower = line.lower()
    if any(k in lower for k in ("kernel", "driver", "nic", "bsod")):
        return "DriverReset"
    if any(k in lower for k in ("cpu", "latency", "timeout", "5xx", "disk", "memory", "redis")):
        return "SystemError"
    if any(k in lower for k in ("deploy", "deployment", "build", "pipeline", "ci", "github actions")):
        return "BuildIssue"
    if "?" in lower or "question" in lower:
        return "Question"
    return "Unknown"


def next_action_from_severity(sev: str) -> str:
    sev = sev.lower()
    if sev == "high":
        return "Escalate to on-call and open an incident channel."
    if sev == "medium":
        return "Create a ticket and monitor for recurrence over the next 24 hours."
    return "Log as informational and watch dashboards for emerging patterns."


def normalize_events(raw_text: str, source: str) -> List[Dict]:
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    events = []
    for line in lines:
        sev = severity_from_line(line)
        cat = category_from_line(line)
        events.append(
            {
                "severity": sev,
                "category": cat,
                "title": line.split("]", 1)[-1].strip() or line,
                "summary": line,
                "next_action": next_action_from_severity(sev),
                "source": source,
                "subsystem": "Unknown",
                "raw": line,
            }
        )
    return events


def severity_rank(sev: str) -> int:
    mapping = {"Low": 0, "Medium": 1, "High": 2}
    return mapping.get(sev, 0)


def render_alert_card(event: Dict):
    sev = event["severity"]
    cat = event["category"]
    title = event["title"]
    next_action = event["next_action"]
    raw = event["raw"]
    source = event["source"]

    sev_class = {
        "High": "pill-high",
        "Medium": "pill-medium",
        "Low": "pill-low",
    }.get(sev, "pill-low")

    html = f"""
    <div class="alert-card">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <div>
                <span class="pill {sev_class}">{sev}</span>
                <span class="pill pill-category">{cat}</span>
            </div>
            <div style="font-size:0.85rem;color:#9CA3AF;">
                Source: <span style="color:#E5E7EB;">{source}</span>
            </div>
        </div>
        <div style="font-weight:600;font-size:0.98rem;margin-bottom:4px;color:#F9FAFB;">
            {title}
        </div>
        <div style="font-size:0.9rem;color:#E5E7EB;margin-bottom:6px;">
            <span style="font-weight:500;">Next:</span> {next_action}
        </div>
        <div style="font-size:0.8rem;color:#9CA3AF;">
            <span style="font-weight:500;color:#6EE7B7;">Raw:</span>
            <code style="font-size:0.75rem;color:#A5B4FC;"> {raw} </code>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# -------------------------------
# Sample data
# -------------------------------
SAMPLE_WINDOWS_BASIC = """[CRITICAL] Kernel-Power event 41 on PROD-01
[WARNING] Disk latency high on DB-02
[INFO] Scheduled backup completed successfully
"""

SAMPLE_WINDOWS_BUSY = """[CRITICAL] Security-Audit: multiple failed logins for svc-deploy on PROD-01
[ERROR] Kernel-Driver reset observed on NIC eth0 (srv-api-03)
[WARNING] High CPU usage detected on cache node REDIS-02
[INFO] Daily security scan completed for PROD subscription
[WARNING] Low free space on volume /var/lib/docker (72% used) on PROD-02
"""

SAMPLE_GITHUB_CI = """[ERROR] GitHub Actions: tests failed in payment-service on main
[WARNING] GitHub Actions: flaky test detected in notification-service
[CRITICAL] GitHub Actions: deploy step failed for api-gateway (rollback triggered)
[INFO] GitHub Actions: lint + typecheck succeeded for auth-service
"""

SAMPLE_MIXED_2AM = """[CRITICAL] PagerDuty: API error rate > 5% on checkout-service
[WARNING] Redis latency > 50ms on cache-cluster-1
[INFO] Cron: nightly ETL completed successfully
[ERROR] GitHub Actions: blue/green deploy failed for web-frontend
"""

# -------------------------------
# UI
# -------------------------------
st.title("AlertLoom Telemetry Triage (Madison Demo)")
st.write(
    "Paste noisy engineering telemetry and let **AlertLoom** surface a few clear, "
    "action-ready alerts — each with one next step, instead of a wall of logs."
)

with st.expander("How this demo works (plain English)", expanded=True):
    st.markdown(
        """
- You paste raw telemetry (logs, events, or JSON-like lines).
- The tool splits it into individual events.
- Each event is classified into a severity (**Low / Medium / High**) and a rough category.
- Only events at or above the selected severity gate show up as alerts with **one next step**.
- This simulates how the Madison agent behind AlertLoom would behave for SRE / ops teams.
        """
    )

st.markdown("---")

left, right = st.columns([1.2, 1])

with left:
    st.subheader("Telemetry input")
    st.caption("Choose a sample or paste your own incident logs.")

    mode = st.radio(
        "What are you triaging?",
        (
            "Sample Windows – basic",
            "Sample Windows – busy on-call hour",
            "Sample GitHub CI failures",
            "Sample mixed: 2AM on-call page",
            "Paste my own logs",
        ),
        index=1,
    )

    if mode == "Sample Windows – basic":
        sample_source = "Windows"
        default_text = SAMPLE_WINDOWS_BASIC
    elif mode == "Sample Windows – busy on-call hour":
        sample_source = "Windows"
        default_text = SAMPLE_WINDOWS_BUSY
    elif mode == "Sample GitHub CI failures":
        sample_source = "GitHub"
        default_text = SAMPLE_GITHUB_CI
    elif mode == "Sample mixed: 2AM on-call page":
        sample_source = "Mixed"
        default_text = SAMPLE_MIXED_2AM
    else:
        sample_source = "Custom"
        default_text = ""

    st.caption(f"Sample source: {sample_source}")
    raw_logs = st.text_area(
        "Paste raw logs or event lines here",
        value=default_text,
        height=180,
        placeholder="[CRITICAL] Kernel-Power event 41 on PROD-01",
    )
    st.caption(
        "Tip: each non-empty line is treated as a separate event. "
        "You can mix severities like [CRITICAL], [ERROR], [WARNING], [INFO]."
    )

with right:
    st.subheader("What this replaces")
    st.markdown(
        """
Without AlertLoom, an on-call engineer might:

- Scroll through hundreds of log lines.
- Manually guess which ones matter.
- Lose minutes before taking action.

This demo shows a friendlier triage view: **a few alerts, each with one recommended next step.**
"""
    )

    st.subheader("Brand note")
    st.markdown(
        """
This interface follows the **AlertLoom** palette:

- Midnight Navy background for a focused, telemetry-dashboard feel.
- Signal Cyan accents for highlights and links.
- A touch of Ops Green for ✅ “good” states.
- Warm white text for readability on dark UIs.

It’s intentionally minimal so hiring managers can focus on behavior, not visual noise.
"""
    )

st.markdown("---")

st.subheader("Minimum severity to show")

severity_gate = st.slider(
    "Alerts at this level or higher will be shown in the triage output.",
    min_value=0,
    max_value=2,
    value=1,
    step=1,
    format="%d",
)

severity_labels = {0: "Low", 1: "Medium", 2: "High"}
st.caption(f"Alerts at **{severity_labels[severity_gate]}** or higher will be shown below.")

run_clicked = st.button("Run AlertLoom triage 🧪", type="primary")

events: List[Dict] = []
alerts: List[Dict] = []

if run_clicked:
    if not raw_logs.strip():
        st.warning("Please paste some logs or choose a sample before running triage.")
    else:
        events = normalize_events(raw_logs, sample_source)
        alerts = [
            e for e in events if severity_rank(e["severity"]) >= severity_gate
        ]

        st.markdown("---")
        st.subheader("Triage output")

        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown('<div class="metric-label">Events scanned</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{len(events)}</div>', unsafe_allow_html=True)
        with m2:
            st.markdown('<div class="metric-label">Alerts returned</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{len(alerts)}</div>', unsafe_allow_html=True)
        with m3:
            st.markdown('<div class="metric-label">Severity gate</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="metric-value">{severity_labels[severity_gate]}</div>',
                unsafe_allow_html=True,
            )

        st.caption(
            "In the full Madison workflow, these alerts would be sent as a single email summary "
            "to the on-call engineer."
        )

        if alerts:
            for event in alerts:
                render_alert_card(event)
        else:
            st.info(
                "No events met the current severity gate. Try lowering the slider or adding more logs."
            )

        # Normalized JSON for reviewers
        with st.expander("Show normalized events (for technical reviewers)"):
            st.write(
                "This is the same normalized event schema that the Madison n8n workflow uses "
                "before applying the severity gate and sending email alerts."
            )
            st.json(events)

# Footer / portfolio link
st.markdown("---")
st.markdown(
    "⬅️ Back to portfolio: "
    "[AlertLoom pilot](https://alertloom-pilot.vercel.app)  ·  "
    "Brand + Madison case study will live on this site."
)
