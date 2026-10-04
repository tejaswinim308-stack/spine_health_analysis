"""
Category / risk analysis & aggregation helpers used by the Risk Analysis
and Insights dashboard pages. Plain pandas aggregation - complements the
raw-SQL examples in sql_engine.py with a few reusable, dataset-agnostic
groupings.
"""
import numpy as np
import pandas as pd

TARGET_COL = "risk_category"


def risk_distribution(df, target_col=TARGET_COL):
    if target_col not in df.columns:
        return {"available": False, "reason": f"Column '{target_col}' not found in dataset."}
    counts = df[target_col].value_counts()
    total = int(counts.sum())
    order = [c for c in ["Low", "Moderate", "High"] if c in counts.index] or list(counts.index)
    return {
        "available": True,
        "categories": order,
        "counts": [int(counts.get(c, 0)) for c in order],
        "pct": [round(100 * counts.get(c, 0) / total, 2) for c in order] if total else [],
        "total": total,
    }


def aggregate_by(df, group_col, agg_col=None, target_col=TARGET_COL):
    """Generic group-by aggregation: mean/median/count of agg_col (or just
    row counts) split by group_col, and, where available, cross-tabbed
    against the risk category target."""
    if group_col not in df.columns:
        return {"available": False, "reason": f"Column '{group_col}' not found."}

    result = {"available": True, "group_col": group_col}

    if agg_col and agg_col in df.columns and pd.api.types.is_numeric_dtype(df[agg_col]):
        g = df.groupby(group_col)[agg_col].agg(["count", "mean", "median", "std"]).round(3)
        g = g.reset_index().rename(columns={"mean": "avg", group_col: "group"})
        result["agg_col"] = agg_col
        result["rows"] = g.where(pd.notnull(g), None).to_dict(orient="records")
    else:
        g = df[group_col].value_counts().reset_index()
        g.columns = ["group", "count"]
        result["agg_col"] = None
        result["rows"] = g.to_dict(orient="records")

    if target_col in df.columns and target_col != group_col:
        crosstab = pd.crosstab(df[group_col], df[target_col])
        result["crosstab"] = {
            "index": list(crosstab.index.astype(str)),
            "columns": list(crosstab.columns.astype(str)),
            "matrix": crosstab.values.tolist(),
        }
    return result


def risk_recommendations(df, target_col=TARGET_COL):
    """
    Simple, transparent, data-driven talking points derived from real
    aggregates in the active dataset - explicitly framed as analytical
    observations, never as medical guidance or diagnosis.
    """
    notes = []
    if target_col not in df.columns:
        return notes

    high = df[df[target_col] == "High"]
    if len(high) == 0:
        return notes

    if "smoking_status" in df.columns:
        smoke_rate_high = (high["smoking_status"] == "Yes").mean() * 100
        smoke_rate_all = (df["smoking_status"] == "Yes").mean() * 100
        if smoke_rate_high - smoke_rate_all > 5:
            notes.append(
                f"Smoking prevalence is {smoke_rate_high:.1f}% within the High-risk segment vs "
                f"{smoke_rate_all:.1f}% dataset-wide - a pattern worth further cohort study."
            )

    if "activity_level" in df.columns:
        sedentary_rate_high = (high["activity_level"] == "Sedentary").mean() * 100
        sedentary_rate_all = (df["activity_level"] == "Sedentary").mean() * 100
        if sedentary_rate_high - sedentary_rate_all > 5:
            notes.append(
                f"Sedentary lifestyle appears in {sedentary_rate_high:.1f}% of High-risk records vs "
                f"{sedentary_rate_all:.1f}% overall, consistent with an activity-related pattern."
            )

    if "bmi" in df.columns:
        bmi_high = high["bmi"].mean()
        bmi_all = df["bmi"].mean()
        if bmi_high - bmi_all > 1:
            notes.append(
                f"Average BMI in the High-risk segment ({bmi_high:.1f}) runs above the dataset "
                f"average ({bmi_all:.1f})."
            )

    if "degree_spondylolisthesis" in df.columns:
        spondy_high = high["degree_spondylolisthesis"].mean()
        spondy_all = df["degree_spondylolisthesis"].mean()
        notes.append(
            f"Mean degree of spondylolisthesis in High-risk records is {spondy_high:.1f} deg, "
            f"compared with {spondy_all:.1f} deg across the full dataset."
        )

    notes.append(
        "These are descriptive, dataset-derived patterns intended for analytical exploration - "
        "not a medical diagnosis or clinical recommendation."
    )
    return notes
