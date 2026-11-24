# Microsoft Exam AI-103: Developing AI Apps & Agents on Azure
## Master Instructor Curriculum, Lab Delivery Guide & AIOps Capstone Teaching Kit

---

## 1. Course Overview & Instructor Delivery Strategy

* **Course Title:** AI-103T00: Developing AI Apps and Agents on Azure
* **Target Audience:** Software Engineers and Data Scientists with existing **Python** proficiency and preferred **Machine Learning** fundamentals.
* **Instructor Role:** Course Architect & Lead Instructor
* **Primary Learning Objectives:**
  1. Equip students to clear **Microsoft Exam AI-103** (Azure AI Apps and Agents Developer Associate).
  2. Shift students' mental models from static ML models to dynamic, stateful **Agentic Architectures & Multi-Agent Swarms**.
  3. Lead students through an end-to-end production capstone: **CloudSentinel AIOps Incident Commander**.

---

## 2. Pedagogical Bridge: Leveraging Students' Python & ML Background

Your students already understand Python, feature vectors, loss functions, and classification. Use these analogies to accelerate learning:

| Traditional ML Concept | Agentic / GenAI Parallel in AI-103 | How to Explain It in Class |
| :--- | :--- | :--- |
| **Feature Embeddings (Word2Vec / ResNet)** | **Vector Search in Azure AI Search** | Embeddings are high-dimensional coordinates. Azure AI Search uses HNSW vector indexing + BM25 hybrid ranking. |
| **Model Inference (`model.predict`)** | **Azure OpenAI Chat Completion** | Prompt tokens + system instructions act as dynamic weights conditioned per request. |
| **Pipeline / Feature Unions** | **RAG & Document Intelligence Pipelines** | Document Intelligence handles raw document ingestion/layout parsing, feeding chunks into vector stores. |
| **Reinforcement Learning / Decision Trees** | **Autonomous Agent Tool Calling** | The LLM acts as the policy network; available tools (functions, code interpreter) represent available actions. |
| **Validation Loss & Precision/Recall** | **Azure AI Foundry Evals** | Groundedness, relevance, coherence, and safety benchmarks evaluated via LLM-as-a-judge. |

---

## 3. Modular Teaching Curriculum (Lecture + Live Demo + Student Lab)

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Course Delivery Matrix                          │
├────────────────────────────────────────────────────────────────────────┤
│ Module 1: Governance, Hubs & Enterprise Security (AI-103 Domain 1)     │
│ Module 2: Azure OpenAI, Prompt Engineering & Safety (Domain 1 & 2)     │
│ Module 3: Hybrid RAG with Azure AI Search & Doc Intel (Domain 2 & 3)   │
│ Module 4: Stateful Agents & Multi-Agent Swarms (Domain 2)              │
│ Module 5: Text, Speech & Multimodal Vision Integration (Domain 4 & 5)  │
│ Module 6: AIOps Capstone Delivery, Code Review & Evaluation (Capstone) │
└────────────────────────────────────────────────────────────────────────┘
```

---

### Module 1: Azure AI Foundry Governance & Enterprise Security
* **Lecture Focus (45 mins):**
  * Architecture of AI Foundry: Hubs vs. Projects vs. Connected Resources.
  * Security model: Microsoft Entra ID, Managed Identities, RBAC roles (Cognitive Services Contributor, OpenAI User).
  * Network security: Virtual Networks, Private Endpoints, and disabling public access.
* **Instructor Live Demo (30 mins):**
  * Provisioning a central AI Foundry Hub via Azure CLI (`az`).
  * Demonstrating Key Vault secret rotation and assigning Managed Identities without API keys.
* **Student Hands-on Lab (60 mins):**
  * *Lab 1.1:* Provision an AI Project, assign user roles, and connect a shared Azure Storage Account securely.

---

### Module 2: Azure OpenAI, Prompt Engineering & Content Safety
* **Lecture Focus (45 mins):**
  * GPT-4o, GPT-4o-mini, and reasoning models (o1/o3-mini).
  * Token economics: TPM/RPM rate limits, context windows, and cost optimization.
  * System prompt engineering, few-shot conditioning, and Pydantic schema-enforced structured outputs.
* **Instructor Live Demo (30 mins):**
  * Live jailbreak simulation (Direct & Indirect prompt injections) in the Playground.
  * Attaching **Azure AI Content Safety** filters to block hate, jailbreak attacks, and hallucinated medical/financial advice.
* **Student Hands-on Lab (60 mins):**
  * *Lab 2.1:* Build a Python microservice with `openai` SDK that validates structured incident JSON and passes inputs through the Content Safety API.

---

### Module 3: Hybrid RAG with Azure AI Search & Document Intelligence
* **Lecture Focus (60 mins):**
  * Advanced chunking: Token-aware vs. markdown hierarchy chunking.
  * Azure AI Search architecture: Vector search (HNSW), BM25 full-text, and the Semantic Reranker.
  * Parsing multi-page unstructured PDFs with Azure AI Document Intelligence.
* **Instructor Live Demo (30 mins):**
  * Uploading a 20-page cloud infrastructure runbook PDF.
  * Extracting layout/tables via Document Intelligence and indexing into Azure AI Search.
  * Showing search result comparison: Pure Vector vs. Hybrid vs. Hybrid + Semantic Reranking.
* **Student Hands-on Lab (75 mins):**
  * *Lab 3.1:* Build an automated ingestion pipeline in Python that extracts tables from PDF runbooks and pushes embeddings (`text-embedding-3-large`) into an Azure AI Search index.

---

### Module 4: Autonomous Agents & Multi-Agent Orchestration
* **Lecture Focus (60 mins):**
  * Assistants API & **Azure AI Agent Service** (Threads, Runs, Tool Callings).
  * Native tools: Code Interpreter (sandboxed Python execution) and File Search.
  * Multi-agent patterns: Sequential, Hierarchical, and Collaborative swarms using **Semantic Kernel** / **AutoGen**.
* **Instructor Live Demo (30 mins):**
  * Live creation of a code-interpreting diagnostic agent that takes a CSV of error logs and plots an anomaly chart in runtime.
* **Student Hands-on Lab (90 mins):**
  * *Lab 4.1:* Implement a 2-agent collaborative loop using `azure-ai-projects`: Agent A diagnoses an error; Agent B drafts a remediation bash script.

---

### Module 5: Multimodal Vision, Text Analytics & Audio
* **Lecture Focus (45 mins):**
  * Azure AI Vision: OCR (Read API) and GPT-4o Multimodal visual reasoning.
  * Azure AI Language: PII redaction (HIPAA/GDPR compliance) and Named Entity Recognition (NER).
  * Azure AI Translator and Speech synthesis.
* **Instructor Live Demo (30 mins):**
  * Inspecting a cloud architecture diagram screenshot using GPT-4o Vision to identify single points of failure.
  * Real-time PII redaction of credentials, IP addresses, and emails from log files.
* **Student Hands-on Lab (60 mins):**
  * *Lab 5.1:* Build an automated log sanitizer that scrubs PII from application traces before sending them to LLM context.

---

### Module 6: Production Capstone – CloudSentinel AIOps Incident Commander
* **Lecture & Scaffolding (45 mins):**
  * Architecture walkthrough: Integrating ML anomaly detection + Vector RAG + Multi-Agent Swarm.
* **Class Execution & Milestones:**
  * Students work through the 4 capstone milestones (detailed below).
* **Instructor Role:**
  * Conducting architectural reviews, debugging token throttle issues, and grading defense presentations.

---

## 4. Classroom Lab Environment & Azure Subscription Strategy

To prevent students from hitting rate limits or running up massive cloud bills, use this architecture:

```
                          [ Master Classroom Azure Subscription ]
                                             │
             ┌───────────────────────────────┴───────────────────────────────┐
             ▼                                                               ▼
┌───────────────────────────────┐                             ┌───────────────────────────────┐
│     Shared Hub Resource Group │                             │ Student Workspaces (Per Pair) │
│ • Azure AI Foundry Hub        │◄────── Connected via ───────┤ • Student AI Project          │
│ • Azure OpenAI Deployment     │        Project Connections  │ • Dedicated Storage Container │
│   (GPT-4o & Embeddings)       │                             │ • Local Python Virtualenv     │
│ • Azure AI Search (Shared Tier)                             │ • Scikit-learn + Agent Code   │
└───────────────────────────────┘                             └───────────────────────────────┘
```

> [!IMPORTANT]
> **Instructor Quota & Cost Management Rules:**
> 1. **Deploy Global Standard or Provisioned instances** of `gpt-4o-mini` for student testing; reserve `gpt-4o` only for final evaluations.
> 2. **Pre-deploy the Azure AI Search Service** on a shared `Standard S1` tier. Provide students with index-level prefixes (e.g., `student01-index`, `student02-index`) to avoid spinning up 20 costly search instances.
> 3. **Enforce Azure Budget Alerts** set to trigger at 50%, 75%, and 90% of your classroom allowance.

---

## 5. AIOps Capstone Project: Instructor Teaching & Grading Kit

### Student Scaffolding Strategy
* **What you provide to students (Starter Kit):**
  1. A synthesized dataset of 50,000 microservice metrics (CPU, RAM, 5xx errors, latency) with injected anomalies.
  2. Sample PDF operational playbooks (Kubernetes crash-loop runbooks, database deadlocks).
  3. Pre-configured Azure connection boilerplate (`DefaultAzureCredential` scripts).
* **What students must build:**
  1. The ML Anomaly Detection model (Isolation Forest / Autoencoder).
  2. The Azure AI Search indexing script with Document Intelligence parsing.
  3. The Multi-Agent Swarm (Triage, Diagnostics, Remediation, Safety).
  4. The Azure AI Foundry automated evaluation harness.

---

### Capstone Grading Rubric (100 Points Total)

| Criteria | Points | Passing Standard |
| :--- | :---: | :--- |
| **1. ML Anomaly Detection Pipeline** | 15 pts | Correctly trains baseline telemetry model; flags anomalies with dynamic thresholding; minimal false positives. |
| **2. Document Ingestion & Hybrid RAG** | 20 pts | Successfully extracts tables/layout from PDF runbooks; achieves grounded retrieval via vector + semantic reranker. |
| **3. Agentic Orchestration & Tool Calling** | 25 pts | Clean multi-agent delegation; state maintained across thread turns; Code Interpreter used effectively for log analysis. |
| **4. Safety, Guardrails & Human Approval** | 15 pts | Destructive commands (`rm -rf`, uncapped restarts) blocked; Azure AI Content Safety active; SRE sign-off gate enforced. |
| **5. Foundry Evals & Observability** | 15 pts | Evaluated on Groundedness (>4.0) and Relevance (>4.0); Application Insights logging agent telemetry. |
| **6. Code Quality & Defense Presentation** | 10 pts | Modular Python code (type hints, error handling, async); articulate explanation of design tradeoffs. |

---

### Common Student Pitfalls & Instructor Troubleshooting

1. **Infinite Agent Loops:**
   * *Symptom:* Student's agent consumes 100k tokens in seconds by calling tools repeatedly without resolving.
   * *Instructor Fix:* Teach students to enforce `max_iterations=5` in agent loops and provide explicit termination instructions in system prompts.
2. **Context Window Overflow in Logs:**
   * *Symptom:* Students dump raw 50MB log files directly into the LLM prompt.
   * *Instructor Fix:* Show them how to use Python (via Code Interpreter or local scripts) to filter for `ERROR` and `FATAL` log levels before prompt injection.
3. **Hallucinated Remediation Commands:**
   * *Symptom:* The agent invents fictitious CLI flags (e.g., `kubectl restart-cluster --hard`).
   * *Instructor Fix:* Show how to configure temperature to `0.0` and enforce strict RAG citations against indexed runbooks.
