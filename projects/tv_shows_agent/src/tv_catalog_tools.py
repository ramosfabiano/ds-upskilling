from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DATA = _PROJECT_ROOT / "data"


def read_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    shows = pd.read_csv(_DATA / "shows.csv")
    panel = pd.read_csv(_DATA / "panel_ratings.csv")
    snapshots = pd.read_csv(_DATA / "rating_snapshots.csv")
    return shows, panel, snapshots


def load_catalog_slice(genre: str = "") -> str:
    """
    Return JSON summary of the catalog: show counts by genre,
    how many are in the panel ("tracked") vs promotion/buzz-only titles,
    and average current external hype (0–10) for buzz-only shows.
    Pass an empty string for genre to include all genres; otherwise filter
    (e.g. Drama, Comedy).
    """
    shows, panel, _ = read_tables()
    if genre and genre.strip():
        m = shows["genre"].str.lower() == genre.strip().lower()
        s = shows.loc[m].copy()
    else:
        s = shows.copy()
    buzz = s[s["panel_status"] == "buzz_only"]
    tracked = s[s["panel_status"] == "tracked"]
    hype = buzz["current_external_hype_10"].replace(0, pd.NA).dropna()
    avg_hype = float(hype.mean()) if not hype.empty else 0.0
    out = {
        "genre_filter": genre or "(all)",
        "shows_total": int(len(s)),
        "buzz_only_count": int(len(buzz)),
        "tracked_count": int(len(tracked)),
        "buzz_share": round(len(buzz) / max(len(s), 1), 3),
        "avg_current_external_hype_10_buzz_only": round(avg_hype, 2),
    }
    return json.dumps(out, ensure_ascii=False)


def compute_genre_panel_stats(genre: str) -> str:
    """
    Panel statistics (0–10) for shows in the genre by joining shows to panel_ratings.
    Returns JSON with count, mean, median, min, max of panel_avg_score_10.
    """
    shows, panel, _ = read_tables()
    g = genre.strip()
    s = shows[shows["genre"].str.lower() == g.lower()]
    merged = s.merge(panel, on="show_id", how="inner")
    scores = merged["panel_avg_score_10"]
    if scores.empty:
        return json.dumps({"error": "no panel-rated shows in genre", "genre": g})
    out = {
        "genre": g,
        "panel_rated_shows": int(len(scores)),
        "mean_panel_score_10": round(float(scores.mean()), 2),
        "median_panel_score_10": round(float(scores.median()), 2),
        "min_panel_score_10": round(float(scores.min()), 2),
        "max_panel_score_10": round(float(scores.max()), 2),
    }
    return json.dumps(out, ensure_ascii=False)


def estimate_recommendation_band(genre: str, num_seasons: int) -> str:
    """
    Estimate a recommended score band (0–10) for buzz-only titles in the genre
    with the given season count, using snapshot history and in-panel comps from CSVs
    (deterministic heuristics, not LLM math).
    """
    shows, panel, snapshots = read_tables()
    g = genre.strip()
    s = shows[
        (shows["genre"].str.lower() == g.lower())
        & (shows["num_seasons"] == int(num_seasons))
    ]
    buzz_ids = s[s["panel_status"] == "buzz_only"]["show_id"]
    snap_scores = snapshots[snapshots["show_id"].isin(buzz_ids)][
        "external_buzz_score_10"
    ]
    merged_tracked = shows[
        (shows["genre"].str.lower() == g.lower())
        & (shows["num_seasons"] == int(num_seasons))
    ].merge(panel, on="show_id")
    in_panel = merged_tracked["panel_avg_score_10"]
    comp_median = float(in_panel.median()) if not in_panel.empty else None
    snap_median = float(snap_scores.median()) if not snap_scores.empty else None
    if snap_median is None and comp_median is None:
        return json.dumps(
            {"error": "insufficient data", "genre": g, "num_seasons": int(num_seasons)}
        )
    base = snap_median if snap_median is not None else comp_median
    spread = 0.05 * base if base else 0
    low = round(base - spread, 2)
    high = round(base + spread, 2)
    out = {
        "genre": g,
        "num_seasons": int(num_seasons),
        "median_recent_external_buzz_10": round(snap_median, 2)
        if snap_median is not None
        else None,
        "median_in_panel_score_10": round(comp_median, 2)
        if comp_median is not None
        else None,
        "recommended_score_band_10": {"low": low, "mid": round(base, 2), "high": high},
        "scale_note": "All scores are 0–10 (synthetic demo).",
    }
    return json.dumps(out, ensure_ascii=False)


def build_comp_table_html(genre: str, num_seasons: int) -> str:
    """
    Build an HTML table of comparable buzz-only shows (same genre and season count)
    with current hype from shows.csv and latest snapshot. Safe for Jupyter via HTML().
    """
    shows, _, snapshots = read_tables()
    g = genre.strip()
    s = shows[
        (shows["genre"].str.lower() == g.lower())
        & (shows["num_seasons"] == int(num_seasons))
        & (shows["panel_status"] == "buzz_only")
    ][["show_id", "service", "episode_count", "current_external_hype_10"]]
    if s.empty:
        return "<p>No buzz-only comps for this slice.</p>"
    last = snapshots.sort_values("snapshot_month").groupby("show_id").tail(1)
    s = s.merge(
        last[["show_id", "external_buzz_score_10", "weeks_in_trending"]],
        on="show_id",
        how="left",
    )
    s = s.rename(columns={"external_buzz_score_10": "last_snapshot_buzz_10"})
    return s.to_html(index=False, border=0, classes="tv-comp-table")
