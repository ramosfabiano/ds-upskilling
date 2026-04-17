from __future__ import annotations

import json
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

import tv_catalog_tools as tools


def build_deterministic_metrics(genre: str, num_seasons: int) -> dict[str, Any]:
    """Single JSON blob fed to the ghostwriter."""
    return {
        "catalog_slice": json.loads(tools.load_catalog_slice(genre)),
        "catalog_all": json.loads(tools.load_catalog_slice("")),
        "panel_stats": json.loads(tools.compute_genre_panel_stats(genre)),
        "recommendation_band": json.loads(
            tools.estimate_recommendation_band(genre, num_seasons)
        ),
        "comp_table_html": tools.build_comp_table_html(genre, num_seasons),
    }


def plot_genre_scores(genre: str) -> plt.Figure:
    """External hype, snapshot buzz, and panel scores by show in the genre."""
    shows, panel, snapshots = tools.read_tables()
    s = shows[shows["genre"].str.lower() == genre.strip().lower()].copy()
    merged = s.merge(panel, on="show_id", how="left")
    last = snapshots.sort_values("snapshot_month").groupby("show_id").tail(1)
    merged = merged.merge(
        last[["show_id", "external_buzz_score_10"]], on="show_id", how="left"
    )
    plot_df = merged.melt(
        id_vars=["show_id", "panel_status"],
        value_vars=[
            "panel_avg_score_10",
            "external_buzz_score_10",
            "current_external_hype_10",
        ],
        var_name="series",
        value_name="score_10",
    )
    plot_df = plot_df.dropna(subset=["score_10"])
    plot_df = plot_df[plot_df["score_10"] > 0]
    plot_df["series"] = plot_df["series"].map(
        {
            "panel_avg_score_10": "panel_avg",
            "external_buzz_score_10": "last_snapshot_buzz",
            "current_external_hype_10": "current_hype_catalog",
        }
    )
    fig, ax = plt.subplots(figsize=(9, 4))
    sns.barplot(data=plot_df, x="show_id", y="score_10", hue="series", ax=ax)
    ax.set_title(f"Rating signals by show — {genre} (0–10, synthetic)")
    ax.set_ylabel("Score (0–10)")
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()
    return fig


GHOSTWRITER_SYSTEM = """You are a senior streaming-catalog curator writing in English.
Rules:
- Use ONLY numbers and facts present in the JSON block labeled METRICS_JSON. Do not invent scores, rankings, or audience claims.
- Scores are always on a 0–10 scale as in the data (say "score", not currency).
- Output short sections: Executive summary, Catalog and gaps, Recommended score band, Next steps (bullet lists).
"""


def _ghostwriter_narrative(client: Any, model: str, bundle: dict[str, Any]) -> str:
    metrics_json = json.dumps(bundle.get("metrics", {}), ensure_ascii=False, indent=2)
    user_content = "METRICS_JSON:\n```json\n" + metrics_json + "\n```\n"
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": GHOSTWRITER_SYSTEM},
            {"role": "user", "content": user_content},
        ],
    )
    return (response.choices[0].message.content or "").strip()


def quality_gate_narrative(
    narrative: str, required_phrases: list[str]
) -> dict[str, Any]:
    """Lightweight reflection gate: require that key anchors appear as substrings."""
    text = narrative.lower()
    missing = [p for p in required_phrases if p.lower() not in text]
    return {"pass": len(missing) == 0, "missing_phrases": missing}


def run_recommendation_pipeline(
    client: Any,
    model: str,
    genre: str,
    num_seasons: int = 2,
) -> dict[str, Any]:
    """
    End-to-end: deterministic metrics, chart, HTML comps, aisuite tool-using analyst step,
    then ghostwriter on frozen JSON.
    """
    metrics = build_deterministic_metrics(genre, num_seasons)
    fig = plot_genre_scores(genre)

    analyst_prompt = (
        f"You are a recommendations analyst for a streaming catalog. Use the tools to inspect "
        f"genre '{genre}' and shows with {num_seasons} season(s). "
        "Then reply with a tight bullet summary in English citing only tool outputs."
    )
    tool_response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": analyst_prompt}],
        tools=[
            tools.load_catalog_slice,
            tools.compute_genre_panel_stats,
            tools.estimate_recommendation_band,
            tools.build_comp_table_html,
        ],
        max_turns=10,
    )
    analyst_text = (tool_response.choices[0].message.content or "").strip()

    bundle = {"metrics": metrics}
    narrative = _ghostwriter_narrative(client, model, bundle)
    band = metrics.get("recommendation_band") or {}
    rec = band.get("recommended_score_band_10") or {}
    mid = rec.get("mid")
    required: list[str] = [genre.strip()]
    if mid is not None:
        required.append(str(mid))
    gate = quality_gate_narrative(narrative, required)

    return {
        "genre": genre,
        "num_seasons": num_seasons,
        "metrics": metrics,
        "analyst_tool_transcript": analyst_text,
        "executive_narrative": narrative,
        "reflection_gate": gate,
        "figure": fig,
    }
