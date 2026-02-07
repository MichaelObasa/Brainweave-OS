# 🧠 Brainweave-OS

**The "Personal Intelligence Layer" for the Knowledge Worker.**
*Concept: Google Drive x Cohere - but private, local, and built for B2C scale.*

---

### 🔮 The Thesis
I’m betting on a future where we need **more** personal compute and storage, not less.

As AI becomes the default interface for information, the competitive advantage for knowledge workers won't be "using AI" - it will be having a **Private Intelligence Layer** that owns your context. We need to capture the flood of unstructured data we consume (YouTube, podcasts, papers) and convert it into a structured, queryable asset.

Current solutions are fragmented. We have storage (Drive), retrieval (Cohere), and chat (ChatGPT), but no unified OS that binds them together for the power user.

**Brainweave-OS** is that binding layer. It is an ingestion engine designed to combine best-in-class inference (GPT-5 mini, DeepSeek, GLM) with reliable personal storage.

---

### 🏗️ Architecture & Capability
Currently, this module functions as a **High-Fidelity YouTube Ingestion Pipeline**.
It treats video content as raw data: extracting transcripts, generating structured metadata via LLMs, and serializing it as clean Markdown in your local vault.

**Key Engineering Principles:**
* **Model Agnostic:** Designed to swap backends easily (e.g., using **DeepSeek v3.2** for reasoning or **GPT-5 mini** for cost-effective summarization).
* **Local-First:** Data is stored in standard Markdown/YAML. You own the bytes, not a SaaS provider.
* **Idempotency:** The pipeline is state-aware; it won't burn API credits re-processing the same video twice.

---

## 🛠️ System Design: The "Staging" Pattern

I designed the I/O layer to handle the specific constraints of cloud-synced filesystems (Google Drive, Dropbox, OneDrive).

**The Problem:**
Writing directly to a synced folder often causes **File Locking** exceptions ( `OSError: [Errno 13]`) when the sync client attempts to upload a file while Python is still writing to it.

**The Solution:**
I implemented a **Two-Stage Write Strategy**:
1.  **Atomic Staging:** The system *always* writes to a local `_staging` directory first. This is fast, strictly local, and prevents partial writes.
2.  **Safe Promotion:** It then attempts to copy the artifact to the `knowledge_vault` (Google Drive).
3.  **Failure Isolation:** If the Vault is locked, the system logs a warning but **does not crash**. The data remains safe in Staging for a later sync.

---

## 🚀 Features

* **Universal Extraction:** Handles standard URLs, Shorts, and auto-captions across multiple languages.
* **Pluggable Intelligence:** Supports multiple provider backends to optimize for cost vs. quality:
    * **OpenAI** (GPT-5.2 / GPT-5 mini)
    * **DeepSeek** (v3.2)
    * **Google** (Gemini 3 Pro / 3 Flash)
    * *Experimental support for high performing agentic open source models like GLM-4.7 and MiniMax 2.1*
* **Structured Enrichment:** Transforms raw text into queryable metadata:
    * **Executive Summary** (TL;DW)
    * **Semantic Tagging** (Topics, Entities, Guests)
    * 💡 **Key Insights** (Bullet-point takeaways)
* **Windows-Safe:** Sanitizes filenames automatically to comply with NTFS restrictions.

---

## ⚙️ Setup

### 1. Requirements
* Python 3.12+
* API Key for your preferred LLM provider.

### 2. Installation
```bash
git clone [https://github.com/yourusername/brainweave-os.git](https://github.com/yourusername/brainweave-os.git)
cd brainweave-os

# Create virtual env
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
