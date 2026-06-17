import os
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

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
        self.model_name = "gemini-2.0-flash"

    def process_ticket_resolution(self, ticket_id: str, raw_logs: List[dict]) -> ResolutionVerdict:
        prompt = f"Analyze this JSM ticket log and synthesize an FAQ article: {str(raw_logs)}"
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ResolutionVerdict,
                temperature=0.0,
            ),
        )
        return ResolutionVerdict.model_validate_json(response.text)