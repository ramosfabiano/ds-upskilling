# TV catalog recommendations agent

Jupyter-based proof of concept for a **ratings and recommendation brief**.

## Prerequisites

- Podman or Docker with Compose v2
- An OpenAI API key for aisuite (`OPENAI_API_KEY`)

## Quick start

Copy env and set `OPENAI_API_KEY`:

```bash
cp .env.example .env

# ... then edit .env
```

Then:

```bash
make build
make up
```

Open the URL indicated, then open `notebooks/tv_catalog_agent.ipynb` and run all cells.

The compose file bind-mounts this project directory so edits to notebooks and `src/` persist on the host.

## Data

Synthetic CSVs under `data/`:

### `shows.csv`

| Column | Meaning |
|--------|---------|
| `show_id` | Unique identifier for the show; join key to the other CSVs. |
| `service` | Streaming service name (e.g. Netflix, HBO). |
| `genre` | Genre label (e.g. Drama, Comedy). |
| `num_seasons` | Number of seasons. |
| `episode_count` | Total episode count. |
| `panel_status` | `tracked` if the show has panel ratings in `panel_ratings.csv`; `buzz_only` if modeled via external buzz only. |
| `current_external_hype_10` | Current external hype on a 0–10 scale; tools use this for buzz-only titles (the sample uses `0` for tracked rows). |

### `panel_ratings.csv`

| Column | Meaning |
|--------|---------|
| `panel_rating_id` | Stable id for this panel rating row. |
| `show_id` | Matches `show_id` in `shows.csv`. |
| `panel_avg_score_10` | Average panel score on a 0–10 scale. |
| `window_start` | Start date (inclusive) of the measurement or validity window. |
| `window_end` | End date (inclusive) of that window. |
| `cohort` | Panel cohort label (e.g. which viewer group produced the score). |


### `rating_snapshots.csv`

| Column | Meaning |
|--------|---------|
| `show_id` | Matches `show_id` in `shows.csv`. |
| `snapshot_month` | Month of the snapshot (`YYYY-MM`). |
| `external_buzz_score_10` | External buzz score for that month on a 0–10 scale. |
| `weeks_in_trending` | Weeks in trending associated with that snapshot (synthetic demo field). |
