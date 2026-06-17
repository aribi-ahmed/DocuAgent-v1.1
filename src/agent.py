import os
import time
import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv

# --- Integration Hook: deterministic grounding evaluator ------------------
# Try a package-relative import first (works when imported as `src.agent`);
# fall back to a flat import so `python src/agent.py` still runs directly.
try:
    from .evaluator import DocuEvaluator
except ImportError:  # pragma: no cover - direct-script execution path
    from evaluator import DocuEvaluator

# Load environment variables from the local .env file
load_dotenv()

# --- Model Consistency Safeguard (Enhancement #4) -------------------------
MODEL_NAME = "gemini-2.5-flash"

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class SourceCitation(BaseModel):
    comment_author: str = Field(description="Username of the engineer.")
    comment_id: str = Field(description="Unique JSM comment ID.")
    extracted_quote: str = Field(description="Evidence snippet used for the FAQ.")


class FAQArticleSchema(BaseModel):
    article_title: str = Field(description="Descriptive title for the FAQ.")
    executive_summary: str = Field(description="Summary of the issue and resolution.")
    root_cause_analysis: str = Field(description="Technical breakdown.")
    step_by_step_resolution: List[str] = Field(description="Ordered list of fix steps.")


class ExplainabilityTrace(BaseModel):
    confidence_score: float = Field(description="Certainty score (0.0-1.0).")
    reasoning_justification: str = Field(description="Rationale for resolution selection.")
    source_citations: List[SourceCitation]


class ResolutionVerdict(BaseModel):
    jira_ticket_id: str
    faq_payload: FAQArticleSchema
    explainability_layer: ExplainabilityTrace


class DocuAgentEngine:
    def __init__(self):
        self.client = genai.Client()
        self.model_name = MODEL_NAME
        self.last_latency_seconds: float = 0.0
        # Deterministic grounding evaluator (no API call, no extra latency).
        self.evaluator = DocuEvaluator()

    def process_ticket_resolution(self, ticket_id: str, raw_logs: List[dict]) -> ResolutionVerdict:
        prompt = f"Analyze this JSM ticket log and synthesize an FAQ article: {str(raw_logs)}"

        # --- Enhancement #2: time only the raw Gemini execution --------------
        start = time.perf_counter()
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ResolutionVerdict,
                temperature=0.0,
            ),
        )
        self.last_latency_seconds = time.perf_counter() - start
        logger.info(
            "Gemini execution for %s completed in %.3fs (model=%s)",
            ticket_id, self.last_latency_seconds, self.model_name,
        )

        verdict = ResolutionVerdict.model_validate_json(response.text)

        # --- Integration Hook: replace the LLM's self-reported confidence ----
        # The model grading its own work is not defensible. We overwrite the
        # confidence_score with a deterministic grounding score derived purely
        # from whether the cited quotes actually exist in the source logs.
        llm_self_reported = verdict.explainability_layer.confidence_score
        grounded_score = self.evaluator.calculate_confidence(
            raw_logs, verdict.explainability_layer.source_citations
        )
        verdict.explainability_layer.confidence_score = grounded_score
        logger.info(
            "Grounding confidence for %s = %.3f (LLM self-reported %.3f over %d citations)",
            ticket_id,
            grounded_score,
            llm_self_reported,
            len(verdict.explainability_layer.source_citations),
        )

        return verdict


if __name__ == "__main__":
    mock_jira_logs = [
        {"id": "101", "user": "support_agent_bob", "text": "Customer says the server is crashing with OutOfMemory errors. Restarting the pod now."},
        {"id": "102", "user": "customer_it", "text": "Restarting didn't work. It crashed again after 10 minutes. Help!"},
        {"id": "103", "user": "senior_dev_sarah", "text": "Looking at the logs. The connection pool max size defaults to 10, causing thread starvation under load. We need to update POOL_MAX to 100 in production.conf."},
        {"id": "104", "user": "support_agent_bob", "text": "Applied Sarah's fix to production.conf and restarted. Memory usage stabilized. Closing ticket."},
    ]

    print("Initializing DocuAgent Live Test Execution...")

    try:
        engine = DocuAgentEngine()
        result = engine.process_ticket_resolution(ticket_id="JSM-4092", raw_logs=mock_jira_logs)

        print("\nSUCCESS! RECEIVED STRUCTURED ARTIFACT FROM GEMINI:")
        print(result.model_dump_json(indent=2))
        print(f"\nLatency: {engine.last_latency_seconds:.3f}s (model={engine.model_name})")
        print(f"Grounded confidence: {result.explainability_layer.confidence_score:.3f}")

    except Exception as e:
        print(f"\nExecution Failed: {str(e)}")