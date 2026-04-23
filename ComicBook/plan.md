Look into the initial draft:

```md
Design Document: LLM-Orchestrated Image Prompt & Generation Workflow 
Version: 1.0
Date: April 23, 2026

1. Overview
The system accepts a user prompt, uses an LLM as the intelligent “brain” to dynamically decide on art-style templates (all, subset, none, or extract new style), generates image prompts, stores them, selectively invokes the local image-generation API only for new prompts, and terminates cleanly.
The design follows the current 2026 standard for reliable, stateful LLM workflows: LangGraph (or its visual layer Langflow) for graph-based orchestration with conditional routing.


2. Architecture
Key architectural design choices: Modular, flexible, reusable components; clear separation of concerns; robust state management; and a single LLM node for all decision-making to ensure consistent context and reasoning.

Graph Structure (LangGraph): Directed graph with nodes for input, LLM routing/decision, template retrieval/storage, prompt generation, parallel image API calls, and end state. Conditional edges route based on LLM output (JSON schema enforced).

State Management: Persistent state (prompts, templates, generated images) stored in local SQLite.
LLM Brain: Single modular LLM node that outputs structured JSON for decisions (selected styles, new prompts, new template to save). Workflow should be able to decide the model to use based on the prompt and context.(example: gpt-5.4 for complex reasoning, gpt-5.4-mini for simpler tasks)

Image Engine: use this script: `DoNotChange/generate_image_gpt_image_1_5.py` as reference for the image generation node, which accepts prompts and returns image paths. 

Execution Flow:
i. User prompt → LLM router
ii. LLM decides template usage + generates prompts
iii. Load/store templates
iv. Parallel image generation calls (new prompts only)
v. End

```

help me create a detailed, end to end validated, researched design and requirement doc.

Then think from different perspective to re-validate this design and requirement document.

This document will be in md format that can be copied.