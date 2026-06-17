# DocuAgent: Autonomous JSM-to-Confluence FAQ Synthesis Engine

Engineering the next layer of intelligent enterprise automation systems for the Atlassian Workspace. Built for the AINS Hackathon 2026.

---

## 🚀 Project Overview

**DocuAgent** bridges a major operational gap in enterprise workflows: the "uncanny valley" of automation where high-value engineering resolutions sit locked away in unstructured, conversational Jira Service Management (JSM) threads. Traditional automation tools (like basic webhooks or keyword routers) cannot touch this problem space because processing, validating, and converting engineering dialogue into professional documentation requires true semantic reasoning and structural synthesis.

DocuAgent is an event-driven, AI-native background engine. The moment an engineering or support ticket changes status to `Closed`, DocuAgent intercepts the full communication history, strips away irrelevant conversational noise, extracts the validated resolution framework, structures it via a strongly typed schema, and generates or appends an auditable FAQ article directly into Confluence.

### 🔴 The AI Imperative
**Remove the AI component from DocuAgent, and the system ceases to function entirely.** It is explicitly not a thin wrapper, nor is it a conversational chatbot. It relies completely on structured LLM orchestration pipelines to perform advanced text transformation, reasoning, and extraction that conventional code patterns cannot reproduce.

---

## 🏗️ Technical Architecture & Core AI Pipeline

DocuAgent processes incoming ticket states through an explicit, multi-stage pipeline utilizing structured extraction layers:

1. **Ingress & Triage:** Intercepts JSM ticket closure webhooks containing raw JSON dumps of conversation logs.
2. **Contextual Distillation:** Filters the conversation logs to isolate critical engineering state changes, troubleshooting sequences, and customer feedback validations.
3. **Structured Synthesis:** Passes processed data through an LLM configuration bound to a rigorous Pydantic metadata schema. This forces the engine to output clean, decoupled documentation metrics alongside an audit trail.
4. **Self-Critique & Scoring:** Computes an extraction confidence score based on explicit token grounding before pushing mutations down to the Confluence API endpoints.

---

## 🛡️ Built-in Explainability & Auditability Layer

In accordance with strict enterprise governance requirements, every single Confluence article created or edited by DocuAgent includes an immutable metadata header detailing its execution lineage:
- **Confidence Tracking:** Explicit certainty ratings generated mathematically via structured validation rules.
- **Source Attributions:** Direct link maps highlighting exactly which comments in the root Jira ticket provided the factual basis for the extracted solution.
- **Reasoning Log:** A clear, human-readable breakdown explaining why the AI prioritized specific technical resolutions over other conversational threads.

---

## 📊 Evaluation & Rigour Framework

To navigate the challenges of non-deterministic systems, DocuAgent applies a dedicated evaluation paradigm:
- **Deterministic Bounds:** Core LLM requests run under strict configurations (Deterministic Seed pinning, Chat Completion JSON constraints, Temperature $T = 0.0$).
- **LLM-As-A-Judge Verification:** A separate validation profile checks generated output structures against raw inputs to actively screen for and mitigate potential hallucinations.

---

## 🛠️ Repository Folder Structure

```text
docuagent/
├── config/
│   └── settings.py
├── src/
│   ├── __init__.py
│   ├── agent.py
│   ├── atlassian_client.py
│   └── evaluator.py
├── tests/
│   └── test_synthetic_payloads.py
├── .env                         # Local environment secrets (GIT-IGNORED)
├── .gitignore                   # Explicit tracking exclusions
├── README.md                    # Project documentation
└── requirements.txt             # Project dependencies and package manifests
