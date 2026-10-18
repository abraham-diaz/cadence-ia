# cadence-ia

A personal training assistant that reads the workouts exported by my **Fitbit** (TCX files),
analyzes the heart-rate curve and tells me how the session went, in the spirit of what Google
does with Gemini, but built by me and running on a Raspberry Pi at home.

It is a mobile-first web app (installable on the iPhone home screen) backed by a small Python API.

## What it does

- **Reads Fitbit TCX exports**: time + heart rate for every sample, plus GPS, altitude and distance
  when the workout has them.
- **Finds sets and rests in strength sessions** from the heart-rate curve alone: HR rises during a
  set and falls during the rest. The detection threshold adapts to each session (5 % of its average
  HR), so it keeps working as fitness improves or for a different person.
- **Measures recovery**: how many bpm the heart rate drops 30 s and 60 s into each rest.
- **Lets you label each workout** with your own types ("Legs", "Upper body", "Walk"…), each one
  either *strength* or *cardio*.
- **Compares each session** with the average of your last 5 sessions of the same type, and charts
  how your average HR and recovery evolve over time.
- **Writes an assessment with an LLM** (Gemini): headline, summary, strengths, things to improve
  and one piece of advice for next time. Only the metrics are sent, never the raw file.

## How it works

```mermaid
flowchart LR
    W[Fitbit] -->|export TCX| I[iCloud Drive]
    I -->|rclone copy<br/>systemd timer| F[TCX folder<br/>on the Pi]
    F -->|cadence-ia ingest| P[Parse + metrics]
    P --> D[(SQLite)]
    D --> A[FastAPI]
    A <-->|metrics as JSON| G[Gemini API]
    A --> R[React PWA<br/>on the phone]
```

1. The watch export lands in an iCloud Drive folder.
2. On the Raspberry Pi, a systemd timer runs `rclone copy` and then `cadence-ia ingest`, which
   parses every TCX not yet in the database, computes its metrics and stores them in SQLite.
3. FastAPI serves the data and the compiled React app on the home network.
4. From the phone you pick the workout type, see the HR curve with the sets shaded, the
   comparison with previous sessions, and ask for the AI assessment.

## Tech stack

| Layer      | Tools |
|------------|-------|
| Backend    | Python 3.11+, FastAPI, Pydantic, SQLite (`sqlite3` from the standard library) |
| Analysis   | Pure Python: TCX parsing with `xml.etree`, resampling, smoothing, zigzag peak detection |
| LLM        | Google Gemini (`google-genai`) with structured JSON output |
| Frontend   | React 19, TypeScript, Vite, React Router, ECharts |
| Deployment | Raspberry Pi 4 (Debian 12), systemd, rclone (iCloud Drive) |
| Tests      | pytest (backend), oxlint (frontend) |

## Repository layout

```
cadence-ia/
├── apps/
│   ├── backend/
│   │   ├── src/cadence_ia/
│   │   │   ├── tcx.py         # TCX parser
│   │   │   ├── metrics.py     # sets/rests detection and recovery
│   │   │   ├── compare.py     # comparison with previous sessions
│   │   │   ├── db.py          # SQLite schema, migrations and queries
│   │   │   ├── ingest.py      # store new TCX files in the database
│   │   │   ├── assessment.py  # LLM assessment (Gemini)
│   │   │   ├── api.py         # FastAPI app
│   │   │   └── cli.py         # `cadence-ia` command
│   │   └── tests/
│   └── frontend/              # React + Vite + TypeScript PWA
└── deploy/                    # Raspberry Pi setup (systemd units, scripts) — coming in step 7
```

## Getting started (development)

Requirements: Python 3.11+, Node.js 20.19+.

### Backend

```bash
cd apps/backend
python -m venv .venv
source .venv/bin/activate          # Windows (Git Bash): source .venv/Scripts/activate
pip install -e ".[dev]"
cp .env.example .env               # then fill in the values (see below)
```

Store your TCX files in the database, then start the API:

```bash
cadence-ia ingest                  # reads CADENCE_DATA_DIR, writes CADENCE_DB
uvicorn cadence_ia.api:app --reload
```

The interactive API docs are at <http://127.0.0.1:8000/docs>.

### Frontend

```bash
cd apps/frontend
npm install
npm run dev
```

Vite proxies `/api` to the backend on port 8000 and listens on the local network, so you can open
`http://<your-pc-ip>:5173` from the phone.

### Configuration

Settings are read from environment variables or from `apps/backend/.env` (never committed; see
`.env.example`):

| Variable           | Default                    | Purpose |
|--------------------|----------------------------|---------|
| `GEMINI_API_KEY`   | –                          | Key for the AI assessment ([get one](https://aistudio.google.com/apikey)) |
| `GEMINI_MODEL`     | `gemini-3.8-flash`         | Gemini model used for the assessment |
| `CADENCE_DATA_DIR` | `~/cadencia-ia/entrada`    | Folder with the `.tcx` files |
| `CADENCE_DB`       | `~/cadencia-ia/cadence.db` | SQLite database file |

For development, point them to the repo, e.g. `CADENCE_DATA_DIR=tests/data` and
`CADENCE_DB=data/cadence.db`.

### Command line

```bash
cadence-ia show path/to/workout.tcx   # print a summary and the sets/rests table
cadence-ia ingest                     # store new TCX files in the database
cadence-ia ingest --force             # re-analyze every file (keeps your workout types)
```

### Tests

```bash
cd apps/backend && pytest             # backend
cd apps/frontend && npm run lint      # frontend
```

The tests build synthetic TCX files, so they run without any personal data. A few extra tests use
a real workout from `tests/data/` and are skipped when it isn't there (TCX files are git-ignored).

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET`    | `/api/sessions` | List sessions, newest first |
| `GET`    | `/api/sessions/{id}` | Session detail: HR curve, sets/rests, stats, comparison, history, assessment |
| `PUT`    | `/api/sessions/{id}/workout-type` | Set (or clear) the session's workout type |
| `POST`   | `/api/sessions/{id}/assessment` | Ask the LLM for a new assessment and store it |
| `GET`    | `/api/workout-types` | List workout types |
| `POST`   | `/api/workout-types` | Create a workout type |
| `PUT`    | `/api/workout-types/{id}` | Rename or re-categorize a type |
| `DELETE` | `/api/workout-types/{id}` | Delete a type (its sessions become unlabeled) |
| `GET`    | `/api/health` | Health check |

## Notes and limitations

- **Heart rate is not load.** In strength training the HR curve shows the pattern of effort and
  rest, not the weight lifted. Fitbit's calories are only an estimate.
- **Fitbit tags every workout as `Sport="Other"`**, which is why the workout type is chosen by hand.
- **Privacy:** on Gemini's free tier, Google may use the requests to improve its products. The app
  only sends aggregated metrics (type, duration, HR, sets, recovery): no GPS, device, file names or
  personal data.
- **Database migrations:** the database stores user data (workout types, assessments), so schema
  changes are versioned migrations in `db.py` (`PRAGMA user_version`), never a rebuild.

## Roadmap

- [x] **1. TCX reader** with a CLI to try it out
- [x] **2. Heart-rate metrics**: sets, rests and recovery, with an adaptive threshold
- [x] **3. REST API** with FastAPI
- [x] **4. Mobile-first frontend**: session list and detail with the HR curve
- [x] **5. SQLite history**: ingestion, workout types (CRUD) and comparisons between sessions
- [x] **6. AI assessment** with Gemini, shown in the frontend
- [ ] **7. Deployment on the Raspberry Pi**: FastAPI serving the built frontend, systemd service,
      rclone + ingest timer, database backups
- [ ] Alerts when the rclone iCloud session expires (ntfy, Telegram…)
- [ ] Cardio sessions: pace, per-km splits, smoothed elevation and a route map coloured by HR
- [ ] Heart-rate zones once the max HR is known
- [ ] Optional notes per workout (exercises, weights, reps) to cross with the HR curve

## Author

Abraham Díaz · [github.com/abraham-diaz](https://github.com/abraham-diaz)
