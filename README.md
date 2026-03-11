# Dragon Ocean Analyzer

**SALA 2026 Hackathon** — Marine Acoustic Monitoring, Galapagos Marine Reserve

> **For full project context (AI or human), read [`PROJECT_OVERVIEW.md`](PROJECT_OVERVIEW.md)**
> For frontend bugs/TODO: [`FRONTEND_AUDIT.md`](FRONTEND_AUDIT.md)
> For backend bugs/TODO: [`BACKEND_AUDIT.md`](BACKEND_AUDIT.md)
> For scientific notes: [`PAPER_NOTES.md`](PAPER_NOTES.md)

---

## What it does

A web dashboard that visualizes the output of a 3-stage AI classifier pipeline (YAMNet → Multispecies Whale → Humpback Whale) applied to 100 underwater recordings. Ranks recordings by biological importance (7-dimension weighted score) so marine biologists know which audio to manually review first.

## Quick Start

```bash
cd frontend
npm install
npm run dev
# http://localhost:3000
```

Vite middleware serves data from `backend/output/`, `backend/output2/`, `backend/data/raw_data/`. No backend server needed.

## Repo Structure

```
hackathon_sala2026/
├── PROJECT_OVERVIEW.md   ← Full context (read first)
├── FRONTEND_AUDIT.md     ← Frontend bugs, TODO, Claude prompts
├── BACKEND_AUDIT.md      ← Backend bugs, TODO, Claude prompts
├── PAPER_NOTES.md        ← Scientific literature notes
├── backend/              ← Python pipeline + data + outputs
└── frontend/             ← React 18 + Vite 6 + Chart.js dashboard
```

## Team Workflow

| Role | Branch | Scope |
|------|--------|-------|
| Frontend A | `feature/pages` | Pages, layout, navigation |
| Frontend B | `feature/viz` | Charts, SpectrogramViewer, visualizations |
| Backend | `feature/pipeline` | Python scripts, data processing |

## For AI Assistants

Read `PROJECT_OVERVIEW.md` first — it contains all schemas, API routes, known bugs, conventions, and a prompt template.
