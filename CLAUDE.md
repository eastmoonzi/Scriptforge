# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Scriptforge is an AI-powered screenplay editor with multi-agent character dialogue generation. The architecture is **FastAPI backend + Next.js frontend + Tauri desktop shell**, powered by Google Gemini (and DeepSeek) as the LLM backend. All UI, comments, prompts, and documentation are in Simplified Chinese.

## Commands

```bash
# Backend (development)
cd backend && pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000

# Frontend (development)
cd frontend && npm install && npm run dev    # Next.js on port 3000

# Tauri desktop (development)
cd src-tauri && cargo tauri dev

# Build Python sidecar binary
./scripts/build_sidecar.sh

# Build Tauri app (includes frontend build)
cd src-tauri && cargo tauri build
```

There is no formal test suite (no pytest/unittest), no linter configuration, and no CI/CD pipeline.

## Architecture

### Three-Tier Architecture

```
src-tauri/              — Tauri desktop shell (Rust)
├── src/lib.rs          — Sidecar lifecycle, file dialogs, commands
├── tauri.conf.json     — Window config, sidecar binary, build hooks
└── binaries/           — PyInstaller-built backend sidecar

frontend/               — Next.js 16 + React 19 + TypeScript + Tailwind
├── src/app/            — Pages (layout.tsx, page.tsx)
├── src/components/     — Editor (TipTap), AIPanel, MenuBar, StatusBar
└── src/lib/            — store.ts (Zustand), api.ts, fountain.ts, autosave.ts

backend/                — FastAPI REST API
├── main.py             — App entry, CORS, router mounting under /api
├── sidecar_entry.py    — Standalone launcher for Tauri sidecar (port 18080)
├── routers/            — generation.py, project.py, export.py, evaluation.py
├── services/           — generation_service.py, director_service.py,
│                         memory_service.py, project_store.py, fountain_export.py
│                         _compat.py (Streamlit mock shim), __init__.py (sys.path)
└── data/               — scriptforge.db (SQLite), chroma/ (vector store)

Root-level modules (kept, imported by backend/services/):
├── template_manager.py — Few-shot drama style templates
├── director_system.py  — Writer/director/character/reviewer pipeline
├── memory_rag.py       — ChromaDB-based RAG memory
├── evaluation_system.py — Dialogue quality metrics (CPD, DE, OOC)
└── templates/          — Drama style template JSON files
```

### Key Design Patterns

**Graceful Degradation Chain**: Every optional feature has `try/except ImportError` guards. The fallback order is: CrewAI multi-agent → sequential LLM calls → mock data (no API key needed).

**Streamlit Compatibility Shim**: Root-level modules originally used `import streamlit as st`. The `backend/services/_compat.py` shim injects a mock `streamlit` module into `sys.modules`, routing UI calls to `logging`.

**Dual Memory System**: Group chat messages are visible to all characters; private chat messages are visible only to the owning character.

**Three-Layer Prompt Composition**:
1. Base: role identity + scene + dual memory + behavioral rules
2. Few-shot: drama style features + example dialogues + anti-patterns (via `template_manager.py`)
3. Management: writer planning → director assignment → character execution → reviewer QC (via `director_system.py`)

### LLM Integration

- Primary: Google Gemini (default model: `gemini-2.0-flash-exp`)
- Secondary: DeepSeek (via OpenAI-compatible client)
- API key: set via `.env` (`GEMINI_API_KEY`) or configured in frontend AI panel
- Embeddings: Google `text-embedding-004` (768-dim) for RAG

### Data Storage

- Projects: SQLite (`backend/data/scriptforge.db`)
- RAG Memory: ChromaDB (`backend/data/chroma/{session_id}`)
- Frontend: localStorage auto-save (5s interval)
- Templates: `templates/` directory (JSON)

## Evaluation Metrics

The evaluation system (`evaluation_system.py`) uses three core metrics:
- **CPD** (Character Personality Divergence): vocabulary diversity + length variance + punctuation style
- **DE** (Dialogue Efficiency): information density + repetition rate + meaningless rate
- **OOC Rate**: LLM-based check for out-of-character speech

## Tech Stack

**Backend**: Python 3.12, FastAPI >= 0.110.0, uvicorn, pydantic, sse-starlette
**AI/ML**: CrewAI >= 1.7.0, langchain-google-genai >= 4.1.0, google-genai >= 1.0.0, ChromaDB >= 0.4.0
**Frontend**: Next.js 16, React 19, TypeScript 5, Tailwind CSS 4, Zustand, TipTap
**Desktop**: Tauri 2, Rust 2021 edition
**Export**: screenplain (Fountain → FDX/HTML/PDF)
