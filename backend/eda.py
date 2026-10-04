"""
Data Scientist layer, part 1: descriptive statistics, outlier analysis,
correlation analysis, and Matplotlib visualizations (returned as base64
PNGs so the Flask API stays JSON-only and the frontend just drops an
<img src="data:image/png;base64,..."> in place).
"""
import base64
import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Dark-theme palette matching the Stitch design system
BG = "#0b1c30"
FG = "#d3e4fe"
GRID = "#26364a"
PRIMARY = "#4d8eff"
SECONDARY = "#03b5d3"
TERTIARY = "#00a572"
WARN = "#F59E0B"
DANGER = "#EF4444"
PALETTE = [PRIMARY, SECONDARY, TERTIARY, WARN, DANGER, "#adc6ff", "#4cd7f6"]


def _fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def _style_axes(ax):
    ax.set_facecolor(BG)
    ax.tick_params(colors=FG, labelsize=8)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.xaxis.label.set_color(FG)
    ax.yaxis.label.set_color(FG)
    ax.title.set_color(FG)
    ax.grid(color=GRID, linewidth=0.6, alpha=0.6)


def descriptive_statistics(df):
    numeric = df.select_dtypes(include=np.number)
    if numeric.empty:
        return []
    desc = numeric.describe().T
    desc["skew"] = numeric.skew()
    desc = desc.round(3)
    desc = desc.reset_index().rename(columns={"index": "column"})
    return desc.to_dict(orient="records")


def outlier_report(df):
    """IQR method: values outside [Q1 - 1.5*IQR, Q3 + 1.5*IQR]."""
    numeric = df.select_dtypes(include=np.number)
    out = []
    for col in numeric.columns:
        series = numeric[col].dropna()
        if series.empty:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        mask = (series < lower) | (series > upper)
        out.append(
            {
                "column": col,
                "q1": round(float(q1), 3),
                "q3": round(float(q3), 3),
                "iqr": round(float(iqr), 3),
                "lower_bound": round(float(lower), 3),
                "upper_bound": round(float(upper), 3),
                "outlier_count": int(mask.sum()),
                "outlier_pct": round(100 * mask.sum() / len(series), 2),
            }
        )
    return sorted(out, key=lambda r: -r["outlier_count"])


def correlation_matrix(df):
    numeric = df.select_dtypes(include=np.number)
    if numeric.shape[1] < 2:
        return {"columns": [], "matrix": []}
    corr = numeric.corr().round(3)
    return {"columns": list(corr.columns), "matrix": corr.values.tolist()}


def correlation_heatmap_png(df):
    numeric = df.select_dtypes(include=np.number)
    if numeric.shape[1] < 2:
        return None
    corr = numeric.corr()

    fig, ax = plt.subplots(figsize=(6.5, 5.5), facecolor=BG)
    ax.set_facecolor(BG)
    im = ax.imshow(corr.values, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.columns)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=7, color=FG)
    ax.set_yticklabels(corr.columns, fontsize=7, color=FG)
    for i in range(len(corr.columns)):
        for j in range(len(corr.columns)):
            ax.text(
                j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center",
                color="white" if abs(corr.values[i, j]) > 0.5 else FG, fontsize=6,
            )
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.yaxis.set_tick_params(color=FG, labelsize=7)
    plt.setp(cbar.ax.get_yticklabels(), color=FG)
    ax.set_title("Feature Correlation Matrix", fontsize=11)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.tight_layout()
    return _fig_to_base64(fig)


def histogram_png(df, column, bins=25):
    if column not in df.columns or not pd.api.types.is_numeric_dtype(df[column]):
        return None
    fig, ax = plt.subplots(figsize=(5.5, 3.6), facecolor=BG)
    _style_axes(ax)
    ax.hist(df[column].dropna(), bins=bins, color=PRIMARY, edgecolor=BG)
    ax.set_title(f"Distribution of {column}", fontsize=10)
    ax.set_xlabel(column)
    ax.set_ylabel("Frequency")
    fig.tight_layout()
    return _fig_to_base64(fig)


def boxplot_png(df, column, group_by=None):
    if column not in df.columns or not pd.api.types.is_numeric_dtype(df[column]):
        return None
    fig, ax = plt.subplots(figsize=(5.5, 3.6), facecolor=BG)
    _style_axes(ax)
    if group_by and group_by in df.columns:
        groups = [g.dropna().values for _, g in df.groupby(group_by)[column]]
        labels = [str(k) for k, _ in df.groupby(group_by)[column]]
        bp = ax.boxplot(groups, labels=labels, patch_artist=True)
        for i, box in enumerate(bp["boxes"]):
            box.set_facecolor(PALETTE[i % len(PALETTE)])
            box.set_alpha(0.75)
        ax.set_title(f"{column} by {group_by}", fontsize=10)
    else:
        bp = ax.boxplot(df[column].dropna().values, patch_artist=True, labels=[column])
        bp["boxes"][0].set_facecolor(PRIMARY)
        ax.set_title(f"Boxplot of {column}", fontsize=10)
    for whisker in bp["whiskers"]:
        whisker.set_color(FG)
    for cap in bp["caps"]:
        cap.set_color(FG)
    for median in bp["medians"]:
        median.set_color("white")
    fig.tight_layout()
    return _fig_to_base64(fig)


def bar_chart_png(df, column, top_n=12):
    if column not in df.columns:
        return None
    counts = df[column].astype(str).value_counts().head(top_n)
    fig, ax = plt.subplots(figsize=(5.5, 3.6), facecolor=BG)
    _style_axes(ax)
    ax.bar(counts.index, counts.values, color=[PALETTE[i % len(PALETTE)] for i in range(len(counts))])
    ax.set_title(f"Count by {column}", fontsize=10)
    ax.set_ylabel("Count")
    plt.setp(ax.get_xticklabels(), rotation=35, ha="right")
    fig.tight_layout()
    return _fig_to_base64(fig)


def scatter_png(df, x, y, hue=None):
    if x not in df.columns or y not in df.columns:
        return None
    fig, ax = plt.subplots(figsize=(5.5, 3.6), facecolor=BG)
    _style_axes(ax)
    if hue and hue in df.columns:
        categories = df[hue].astype(str).unique()
        for i, cat in enumerate(categories):
            sub = df[df[hue].astype(str) == cat]
            ax.scatter(sub[x], sub[y], s=14, alpha=0.75, color=PALETTE[i % len(PALETTE)], label=str(cat))
        legend = ax.legend(fontsize=7, facecolor=BG, edgecolor=GRID, labelcolor=FG)
    else:
        ax.scatter(df[x], df[y], s=14, alpha=0.75, color=PRIMARY)
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.set_title(f"{y} vs {x}", fontsize=10)
    fig.tight_layout()
    return _fig_to_base64(fig)


def eda_charts_bundle(df, category_col=None):
    """A default set of charts for the EDA dashboard page."""
    numeric_cols = list(df.select_dtypes(include=np.number).columns)
    charts = {}

    if numeric_cols:
        charts["histogram"] = {
            "column": numeric_cols[0],
            "image": histogram_png(df, numeric_cols[0]),
        }
    if len(numeric_cols) >= 2:
        charts["scatter"] = {
            "x": numeric_cols[0],
            "y": numeric_cols[1],
            "image": scatter_png(df, numeric_cols[0], numeric_cols[1], hue=category_col),
        }
    if numeric_cols and category_col and category_col in df.columns:
        charts["boxplot"] = {
            "column": numeric_cols[-1],
            "group_by": category_col,
            "image": boxplot_png(df, numeric_cols[-1], group_by=category_col),
        }
    if category_col and category_col in df.columns:
        charts["bar"] = {"column": category_col, "image": bar_chart_png(df, category_col)}
    charts["correlation_heatmap"] = {"image": correlation_heatmap_png(df)}
    return charts
