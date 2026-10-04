"""
Data Analyst layer: ingestion helpers, data-quality profiling, and the
cleaning pipeline. Pure pandas / numpy - no SQL, no ML here.
"""
import numpy as np
import pandas as pd


def load_csv(path_or_buffer):
    """Read a CSV (or TSV, auto-detected) into a DataFrame."""
    df = pd.read_csv(path_or_buffer, sep=None, engine="python")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def dataset_preview(df, n=10):
    """First n rows as JSON-safe records, plus shape."""
    preview = df.head(n).copy()
    preview = preview.where(pd.notnull(preview), None)
    return {
        "columns": list(df.columns),
        "rows": preview.to_dict(orient="records"),
        "n_rows": int(df.shape[0]),
        "n_columns": int(df.shape[1]),
    }


def dtype_report(df):
    """Detected pandas dtype + an inferred semantic type per column."""
    report = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        n_unique = int(df[col].nunique(dropna=True))
        if pd.api.types.is_numeric_dtype(df[col]):
            semantic = "numeric"
        elif pd.api.types.is_bool_dtype(df[col]):
            semantic = "boolean"
        elif n_unique <= max(15, int(0.05 * len(df))):
            semantic = "categorical"
        else:
            semantic = "text / identifier"
        report.append(
            {
                "column": col,
                "pandas_dtype": dtype,
                "semantic_type": semantic,
                "unique_values": n_unique,
            }
        )
    return report


def missing_value_report(df):
    total = len(df)
    out = []
    for col in df.columns:
        n_missing = int(df[col].isna().sum())
        out.append(
            {
                "column": col,
                "missing_count": n_missing,
                "missing_pct": round(100 * n_missing / total, 2) if total else 0.0,
            }
        )
    return sorted(out, key=lambda r: -r["missing_count"])


def duplicate_report(df):
    n_dupes = int(df.duplicated().sum())
    dupe_rows = df[df.duplicated(keep=False)].sort_values(list(df.columns)).head(20)
    dupe_rows = dupe_rows.where(pd.notnull(dupe_rows), None)
    return {
        "duplicate_count": n_dupes,
        "duplicate_pct": round(100 * n_dupes / len(df), 2) if len(df) else 0.0,
        "sample_rows": dupe_rows.to_dict(orient="records"),
    }


def clean_dataset(df):
    """
    Deterministic, explainable cleaning pipeline:
      1. Drop exact duplicate rows
      2. Strip whitespace on string/object columns
      3. Impute numeric NaNs with column median
      4. Impute categorical/object NaNs with column mode
      5. Cast obviously-numeric object columns to numeric

    Returns (cleaned_df, log) where log is a list of human-readable steps
    describing exactly what was changed, for transparency in the UI.
    """
    log = []
    work = df.copy()

    before = len(work)
    work = work.drop_duplicates()
    removed = before - len(work)
    if removed:
        log.append(f"Removed {removed} exact duplicate row(s).")
    else:
        log.append("No exact duplicate rows found.")

    for col in work.select_dtypes(include="object").columns:
        work[col] = work[col].astype(str).where(work[col].notna(), np.nan)
        work[col] = work[col].apply(lambda v: v.strip() if isinstance(v, str) else v)

    # Attempt to coerce object columns that are actually numeric
    for col in work.select_dtypes(include="object").columns:
        coerced = pd.to_numeric(work[col], errors="coerce")
        non_null = work[col].notna().sum()
        if non_null > 0 and coerced.notna().sum() >= 0.95 * non_null:
            work[col] = coerced
            log.append(f"Column '{col}' detected as numeric and converted.")

    numeric_cols = work.select_dtypes(include=np.number).columns
    for col in numeric_cols:
        n_missing = int(work[col].isna().sum())
        if n_missing:
            median_val = work[col].median()
            work[col] = work[col].fillna(median_val)
            log.append(
                f"Filled {n_missing} missing value(s) in '{col}' with median ({median_val:.2f})."
            )

    cat_cols = work.select_dtypes(include="object").columns
    for col in cat_cols:
        n_missing = int(work[col].isna().sum())
        if n_missing:
            mode_series = work[col].mode(dropna=True)
            mode_val = mode_series.iloc[0] if not mode_series.empty else "Unknown"
            work[col] = work[col].fillna(mode_val)
            log.append(f"Filled {n_missing} missing value(s) in '{col}' with mode ('{mode_val}').")

    log.append(f"Final cleaned shape: {work.shape[0]} rows x {work.shape[1]} columns.")
    return work, log


def engineer_features(df):
    """
    Feature engineering for the modeling stage. Adds a small set of derived,
    interpretable features when the expected spine-analytics columns are
    present; safely no-ops (returns df unchanged) for columns it can't find,
    so the pipeline still works on arbitrary uploaded CSVs.
    """
    work = df.copy()
    notes = []

    if {"pelvic_incidence", "sacral_slope"}.issubset(work.columns):
        work["pi_ss_ratio"] = work["pelvic_incidence"] / work["sacral_slope"].replace(0, np.nan)
        work["pi_ss_ratio"] = work["pi_ss_ratio"].fillna(work["pi_ss_ratio"].median())
        notes.append("pi_ss_ratio = pelvic_incidence / sacral_slope")

    if "degree_spondylolisthesis" in work.columns:
        work["spondylolisthesis_flag"] = (work["degree_spondylolisthesis"] > 25).astype(int)
        notes.append("spondylolisthesis_flag = 1 if degree_spondylolisthesis > 25 deg")

    if "bmi" in work.columns:
        work["bmi_band"] = pd.cut(
            work["bmi"],
            bins=[0, 18.5, 25, 30, np.inf],
            labels=["Underweight", "Normal", "Overweight", "Obese"],
        ).astype(str)
        notes.append("bmi_band = WHO BMI banding derived from bmi")

    if "age" in work.columns:
        work["age_band"] = pd.cut(
            work["age"],
            bins=[0, 30, 45, 60, np.inf],
            labels=["<30", "30-45", "46-60", "60+"],
        ).astype(str)
        notes.append("age_band = coarse age bucket derived from age")

    return work, notes
