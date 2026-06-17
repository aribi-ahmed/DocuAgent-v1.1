"""
DocuAgent — Synthetic Evaluation Harness
========================================

Production-grade evaluation pipeline for the DocuAgent JSM-to-Confluence engine.

Running the full evaluation (generates artifacts, logs, and the dashboard):
    python tests/test_synthetic_payloads.py

Running just the structural unit test:
    python -m unittest tests.test_synthetic_payloads

Outputs (all anchored to this file's directory, not the current working dir):
    tests/artifacts/output_<TICKET>.json   # per-ticket structured payloads
    tests/test_run.log                      # timestamped metrics + status log
    tests/confidence_report.png             # two-panel confidence/latency dashboard

NOTE: Each ticket triggers a live Gemini call, so a valid API key in .env and network access are required.
"""

import sys
import time
import logging
import unittest
from pathlib import Path

# --- Path bootstrap: make the harness CWD-independent ----------------------
TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent import DocuAgentEngine, MODEL_NAME  # noqa: E402

# --- Enhancement #1: Smart Artifact Management -----------------------------
ARTIFACTS_DIR = TESTS_DIR / "artifacts"
LOG_FILE = TESTS_DIR / "test_run.log"
DASHBOARD_FILE = TESTS_DIR / "confidence_report.png"

# --- Enhancement #2: High-Fidelity Metrics Logging -------------------------
logger = logging.getLogger("docuagent.eval")


def configure_logging() -> logging.Logger:
    """Wire up file + console logging and ensure the artifacts dir exists."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)

    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Route the engine's own per-call latency logs into the same file.
    engine_logger = logging.getLogger("src.agent")
    engine_logger.setLevel(logging.INFO)
    engine_logger.handlers.clear()
    engine_logger.addHandler(file_handler)

    return logger


# --- Synthetic evaluation dataset ------------------------------------------
# Deliberately messy, multi-author threads that mimic real JSM resolutions.
SYNTHETIC_DATASET = [
    {
        "ticket_id": "JSM-DB-881",
        "logs": [
            {"id": "201", "user": "support_agent_bob", "text": "Customer reports the API returns 500s during peak hours. Connections seem to hang."},
            {"id": "202", "user": "customer_it", "text": "It's intermittent — works fine off-peak, dies under load around 2pm."},
            {"id": "203", "user": "senior_dev_sarah", "text": "Connection pool max size defaults to 10. Under load we exhaust it and threads starve. Bump POOL_MAX to 100 in production.conf."},
            {"id": "204", "user": "support_agent_bob", "text": "Set POOL_MAX=100 and rolled the deployment. Error rate dropped to zero. Closing."},
        ],
    },
    {
        "ticket_id": "JSM-MEM-742",
        "logs": [
            {"id": "301", "user": "customer_it", "text": "Worker pods keep getting OOMKilled every ~30 minutes."},
            {"id": "302", "user": "devops_lee", "text": "JVM heap is unbounded and the container limit is 512Mi. Set -Xmx384m and raise the memory limit to 768Mi."},
            {"id": "303", "user": "customer_it", "text": "Applied both changes. No restarts in 6 hours now. Thanks."},
        ],
    },
    {
        "ticket_id": "JSM-TLS-509",
        "logs": [
            {"id": "401", "user": "support_agent_bob", "text": "Users see 'certificate expired' errors on the checkout domain."},
            {"id": "402", "user": "secops_amir", "text": "The cert-manager renewal job silently failed due to a rate-limited ACME challenge. Re-issued manually and re-enabled the renewal CronJob."},
            {"id": "403", "user": "secops_amir", "text": "New cert valid for 90 days, auto-renew confirmed working. Resolved."},
        ],
    },
    {
        "ticket_id": "JSM-DISK-318",
        "logs": [
            {"id": "501", "user": "customer_it", "text": "Logging service stopped writing. App still up but no new logs."},
            {"id": "502", "user": "devops_lee", "text": "Disk at 100%. Old rotated logs never purged. Added logrotate with a 7-day retention and ran an immediate cleanup."},
            {"id": "503", "user": "customer_it", "text": "Disk back to 40%, logs flowing again. Closing ticket."},
        ],
    },
]


def build_dashboard(ticket_ids, confidences, latencies) -> None:
    """Enhancement #3: render a two-panel confidence/latency dashboard PNG."""
    import matplotlib
    matplotlib.use("Agg")  # headless backend — no display required
    import matplotlib.pyplot as plt

    # Clean tech palette
    CONF_COLOR = "#2563EB"   # blue
    LAT_COLOR = "#0D9488"    # teal
    GRID_COLOR = "#CBD5E1"   # slate-300
    EDGE_COLOR = "#1E293B"   # slate-800

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor("white")
    fig.suptitle(
        "DocuAgent — Synthetic Evaluation Dashboard",
        fontsize=16, fontweight="bold", color=EDGE_COLOR,
    )

    # --- Chart A: Model Confidence Scores --------------------------------
    bars_a = ax_a.bar(ticket_ids, confidences, color=CONF_COLOR,
                      edgecolor=EDGE_COLOR, linewidth=0.6, zorder=3)
    ax_a.set_title("Model Confidence Scores", fontsize=12, fontweight="bold")
    ax_a.set_ylabel("Confidence (0.0 – 1.0)")
    ax_a.set_xlabel("Ticket ID")
    ax_a.set_ylim(0, 1.12)
    ax_a.grid(axis="y", color=GRID_COLOR, linestyle="--", linewidth=0.7, zorder=0)
    ax_a.bar_label(bars_a, fmt="%.2f", padding=3, fontsize=9, fontweight="bold")

    # --- Chart B: Processing Latency -------------------------------------
    bars_b = ax_b.bar(ticket_ids, latencies, color=LAT_COLOR,
                      edgecolor=EDGE_COLOR, linewidth=0.6, zorder=3)
    ax_b.set_title("Processing Latency (Seconds)", fontsize=12, fontweight="bold")
    ax_b.set_ylabel("Latency (s)")
    ax_b.set_xlabel("Ticket ID")
    headroom = (max(latencies) * 1.25) if latencies else 1.0
    ax_b.set_ylim(0, headroom)
    ax_b.grid(axis="y", color=GRID_COLOR, linestyle="--", linewidth=0.7, zorder=0)
    ax_b.bar_label(bars_b, fmt="%.2fs", padding=3, fontsize=9, fontweight="bold")

    for ax in (ax_a, ax_b):
        ax.set_facecolor("#F8FAFC")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        plt.setp(ax.get_xticklabels(), rotation=20, ha="right")

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(DASHBOARD_FILE, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)


def run_evaluation():
    """Execute the full synthetic dataset and emit artifacts, logs, dashboard."""
    log = configure_logging()
    log.info("=" * 60)
    log.info("DocuAgent evaluation run started (model=%s)", MODEL_NAME)

    engine = DocuAgentEngine()
    ticket_ids, confidences, latencies = [], [], []

    for case in SYNTHETIC_DATASET:
        tid = case["ticket_id"]
        try:
            harness_start = time.perf_counter()
            verdict = engine.process_ticket_resolution(tid, case["logs"])
            harness_latency = time.perf_counter() - harness_start

            # Prefer the engine's measurement of the raw API call; fall back
            # to the harness-level timing if it's unavailable.
            latency = engine.last_latency_seconds or harness_latency
            confidence = float(verdict.explainability_layer.confidence_score)

            # Enhancement #1: persist the structured payload into tests/artifacts/
            out_path = ARTIFACTS_DIR / f"output_{tid}.json"
            out_path.write_text(verdict.model_dump_json(indent=2), encoding="utf-8")

            log.info(
                "OK   %-12s | confidence=%.3f | latency=%.3fs | saved=%s",
                tid, confidence, latency, out_path.relative_to(PROJECT_ROOT),
            )

            ticket_ids.append(tid)
            confidences.append(confidence)
            latencies.append(latency)

        except Exception as exc:
            # One bad ticket shouldn't abort the whole evaluation run.
            log.error("FAIL %-12s | %s: %s", tid, type(exc).__name__, exc)

    if ticket_ids:
        build_dashboard(ticket_ids, confidences, latencies)
        log.info("Dashboard written to %s", DASHBOARD_FILE.relative_to(PROJECT_ROOT))
        avg_conf = sum(confidences) / len(confidences)
        avg_lat = sum(latencies) / len(latencies)
        log.info("Summary: %d/%d tickets ok | avg_confidence=%.3f | avg_latency=%.3fs",
                 len(ticket_ids), len(SYNTHETIC_DATASET), avg_conf, avg_lat)
    else:
        log.warning("No successful tickets — skipping dashboard generation.")

    log.info("DocuAgent evaluation run complete")
    log.info("=" * 60)
    return ticket_ids, confidences, latencies


class TestDocuAgent(unittest.TestCase):
    """Lightweight structural test (hits the live API, as before)."""

    def test_synthesis_logic(self):
        engine = DocuAgentEngine()
        mock_logs = [{"id": "1", "user": "dev", "text": "Resolution: Increase heap size."}]

        result = engine.process_ticket_resolution("TEST-123", mock_logs)

        # Verify the structure matches our enterprise requirements
        self.assertIsNotNone(result.faq_payload.article_title)
        self.assertGreater(result.explainability_layer.confidence_score, 0.5)
        # Latency must have been recorded by the engine hook.
        self.assertGreaterEqual(engine.last_latency_seconds, 0.0)


if __name__ == "__main__":
    run_evaluation()
