# Dragon Ocean Analyzer

**SALA 2026 Hackathon** — Marine Acoustic Monitoring, Galapagos Marine Reserve

> **Full project context (AI or human):** [`docs/PROJECT_OVERVIEW.md`](docs/PROJECT_OVERVIEW.md)
> **Frontend bugs/TODO:** [`docs/FRONTEND_AUDIT.md`](docs/FRONTEND_AUDIT.md)
> **Scientific notes:** [`docs/PAPER_NOTES.md`](docs/PAPER_NOTES.md)

---

## What it does

A web dashboard that visualizes the output of a 6-stage AI pipeline applied to underwater hydrophone recordings. Ranks audio clips by biological importance (9-dimension weighted score, 5 tiers) so marine biologists know which recordings to manually review first.

**Pipeline:** AudioClipper → YAMNet → Multispecies Whale → Humpback Whale → Soundscape Indices → Embedding Clusters → Biological Importance Ranking

## Quick Start

### Frontend
```bash
cd frontend
npm install
npm run dev
# http://localhost:3000
```

Vite middleware serves data from `outputs/` via `/api/pipeline/*`. No backend server needed.

### Backend (re-run pipeline)
```bash
pip install -r requirements.txt
python -m backend.run --source hackathon_data/marine-acoustic
```

For GPU environments (RunPod):
```bash
bash scripts/runpod_run.sh --source /workspace/data/marine-acoustic
```

## Repo Structure

```
dragon-ocean-analyzer/
├── README.md
├── LICENSE
├── requirements.txt
├── .gitignore
│
├── backend/          ← Python ML pipeline (stages 0-6)
├── frontend/         ← React 18 + Vite 6 + Chart.js
├── scripts/          ← Data download, deployment utilities
├── docs/             ← Project documentation and audits
│
├── hackathon_data/   ← Audio dataset (gitignored, download separately)
└── outputs/  ← Generated artifacts (gitignored)
```

## Team Workflow

| Role | Scope |
|------|-------|
| Backend | `backend/` — Python pipeline, config, stages |
| Frontend | `frontend/src/` — React components, charts, pages |
| DevOps | `scripts/` — data download, deployment |

## For AI Assistants

Read `docs/PROJECT_OVERVIEW.md` first — it contains all schemas, API routes, known bugs, conventions, and a prompt template.
