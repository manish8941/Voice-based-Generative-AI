"""
Insight & Document Generation Engine
Transforms raw spoken transcripts and RAG context into structured, production-ready engineering specifications:
PRD.md, architecture.md, flow.md, tech_stack.md, tasks.md, and implementation_plan.md.
"""

import json
from typing import Dict, List, Optional
import requests
from groq import Groq

from src.config import (
    DEFAULT_GROQ_LLM_MODEL,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_OLLAMA_MODEL,
    GROQ_API_KEY,
    OLLAMA_HOST,
)


class InsightEngine:
    """Orchestrates LLM calls to transform spoken transcripts and RAG context into engineering artifacts."""

    def __init__(
        self,
        provider: str = DEFAULT_LLM_PROVIDER,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        ollama_host: str = OLLAMA_HOST,
    ):
        self.provider = provider.lower()
        self.api_key = api_key or GROQ_API_KEY
        self.model = model or (
            DEFAULT_GROQ_LLM_MODEL if self.provider == "groq" else DEFAULT_OLLAMA_MODEL
        )
        self.ollama_host = ollama_host
        self._groq_client: Optional[Groq] = None

    def set_api_key(self, api_key: str):
        self.api_key = api_key
        self._groq_client = None

    @property
    def groq_client(self) -> Groq:
        if self._groq_client is None:
            if not self.api_key:
                raise ValueError("Groq API Key is missing. Please set GROQ_API_KEY.")
            self._groq_client = Groq(api_key=self.api_key)
        return self._groq_client

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Internal dispatch to either Groq or Ollama."""
        if self.provider == "groq":
            response = self.groq_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_completion_tokens=4096,
            )
            return response.choices[0].message.content or ""
        elif self.provider == "ollama":
            url = f"{self.ollama_host}/api/generate"
            payload = {
                "model": self.model,
                "prompt": f"System: {system_prompt}\n\nUser: {user_prompt}",
                "stream": False,
                "options": {"temperature": 0.2},
            }
            res = requests.post(url, json=payload, timeout=120)
            res.raise_for_status()
            return res.json().get("response", "")
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def generate_prd(self, transcript: str, rag_context: str = "") -> str:
        """Generate PRD.md from transcript."""
        system_prompt = (
            "You are a Principal Technical Product Manager. Your job is to transform a raw spoken voice note / brain-dump "
            "into a comprehensive, highly detailed, production-grade Project Requirements Document (PRD.md). "
            "Clean up disfluencies, structure ambiguities, define concrete acceptance criteria, and output in clean GitHub Flavored Markdown."
        )
        user_prompt = f"""Spoken Voice Transcript:
\"\"\"
{transcript}
\"\"\"

{rag_context}

Generate a comprehensive PRD.md with the following sections:
# Project Requirements Document (PRD): [Project Title]
## 1. Executive Summary & Problem Statement
## 2. Goals & Success Metrics (KPIs)
## 3. User Personas & Core Workflows
## 4. Functional Requirements (Categorized with Priority P0/P1/P2)
## 5. Non-Functional Requirements (Performance, Security, Reliability)
## 6. Edge Cases & Constraints
## 7. Assumptions & Out of Scope
"""
        return self._call_llm(system_prompt, user_prompt)

    def generate_architecture(self, transcript: str, rag_context: str = "") -> str:
        """Generate architecture.md from transcript."""
        system_prompt = (
            "You are a Lead Software Architect. Your job is to convert spoken requirements and system thoughts "
            "into an exhaustive technical Architecture Document (architecture.md). Include concrete component boundaries, "
            "Mermaid architecture diagrams, data models, API endpoints, and security considerations."
        )
        user_prompt = f"""Spoken Voice Transcript:
\"\"\"
{transcript}
\"\"\"

{rag_context}

Generate an exhaustive architecture.md with the following structure:
# System Architecture Document: [Project Title]
## 1. High-Level Architectural Overview
## 2. System Component Diagram (Include a complete, valid Mermaid `graph TD` or `flowchart TD` block)
## 3. Core Modules & Responsibilities
## 4. Data Flow & State Management
## 5. API Contracts & Interface Definitions (Endpoints / Types)
## 6. Data Storage & Schema Design
## 7. Security, Error Handling & Failure Recovery
"""
        return self._call_llm(system_prompt, user_prompt)

    def generate_flow(self, transcript: str, rag_context: str = "") -> str:
        """Generate flow.md with detailed execution order and Mermaid sequence diagrams."""
        system_prompt = (
            "You are a Senior Systems Engineer. Create a detailed Flow and Execution Specification (flow.md) "
            "describing entry points, sequence of calls, state transitions, and Mermaid sequence diagrams."
        )
        user_prompt = f"""Spoken Voice Transcript:
\"\"\"
{transcript}
\"\"\"

{rag_context}

Generate a comprehensive flow.md containing:
# Execution Flow & Lifecycle Specification
## 1. System Entry Points & Initialization Order
## 2. End-to-End Execution Sequence (Include a complete Mermaid `sequenceDiagram` block)
## 3. Component Interaction & Function Call Hierarchy
## 4. State Transition & Lifecycle Diagram (Include Mermaid `stateDiagram-v2`)
## 5. Error Recovery & Exception Handling Flows
"""
        return self._call_llm(system_prompt, user_prompt)

    def generate_tech_stack(self, transcript: str, rag_context: str = "") -> str:
        """Generate tech_stack.md with stack decisions, dependencies, and setup steps."""
        system_prompt = (
            "You are a Principal Software Engineer. Create an exhaustive Tech Stack and Environment Setup Document (tech_stack.md). "
            "Specify every framework, library, tool, setup command, and rationale."
        )
        user_prompt = f"""Spoken Voice Transcript:
\"\"\"
{transcript}
\"\"\"

{rag_context}

Generate a detailed tech_stack.md containing:
# Technology Stack & Environment Setup
## 1. Core Technology Choices & Rationale (Table format)
## 2. Dependency Matrix (Required packages and versions)
## 3. Environment Variables & Secret Configuration
## 4. Local Development Setup Guide (Step-by-step CLI commands)
## 5. Build, Lint & Packaging Instructions
"""
        return self._call_llm(system_prompt, user_prompt)

    def generate_tasks(self, transcript: str, rag_context: str = "") -> str:
        """Generate tasks.md with an actionable phased checklist."""
        system_prompt = (
            "You are an Agile Technical Lead. Convert the spoken requirements into a prioritized, actionable "
            "engineering task breakdown in Markdown checklist format (`- [ ]`)."
        )
        user_prompt = f"""Spoken Voice Transcript:
\"\"\"
{transcript}
\"\"\"

{rag_context}

Generate a structured tasks.md with:
# Engineering Action Plan & Task Breakdown
## Phase 1: Environment Setup & Core Foundations
## Phase 2: Core Engine & Data Pipelines
## Phase 3: Interface & Integration Layer
## Phase 4: Testing, Error Handling & Polish
## Phase 5: Deployment & Documentation
(Ensure each task is written as a clear checkbox `- [ ]` with sub-tasks and acceptance criteria.)
"""
        return self._call_llm(system_prompt, user_prompt)

    def generate_implementation_plan(self, transcript: str, rag_context: str = "") -> str:
        """Generate implementation_plan.md."""
        system_prompt = (
            "You are a Technical Project Manager. Create an engineering Implementation Plan (implementation_plan.md) "
            "focusing on execution strategy, risk mitigation, test verification, and rollback procedures."
        )
        user_prompt = f"""Spoken Voice Transcript:
\"\"\"
{transcript}
\"\"\"

{rag_context}

Generate a complete implementation_plan.md with:
# Implementation & Delivery Plan
## 1. Implementation Strategy & Milestones
## 2. Phased Rollout Schedule
## 3. Automated & Manual Verification Plan
## 4. Risk Analysis & Mitigation Matrix
## 5. Rollback & Disaster Recovery Procedures
"""
        return self._call_llm(system_prompt, user_prompt)

    def generate_all(self, transcript: str, rag_context: str = "") -> Dict[str, str]:
        """Generate all 6 core documentation artifacts in sequence."""
        return {
            "prd.md": self.generate_prd(transcript, rag_context),
            "architecture.md": self.generate_architecture(transcript, rag_context),
            "flow.md": self.generate_flow(transcript, rag_context),
            "tech_stack.md": self.generate_tech_stack(transcript, rag_context),
            "tasks.md": self.generate_tasks(transcript, rag_context),
            "implementation_plan.md": self.generate_implementation_plan(transcript, rag_context),
        }
