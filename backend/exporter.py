"""
Export helpers: cleaned CSV, an R-friendly CSV (factor-safe column names,
no index), and a flat CSV tuned for BI tools like Tableau / Power BI
(category columns kept as plain strings, no special characters in headers).
"""
import os
import re

EXPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "exports")
EXPORT_DIR = os.path.abspath(EXPORT_DIR)
os.makedirs(EXPORT_DIR, exist_ok=True)


def _safe_colname(col):
    col = re.sub(r"[^0-9a-zA-Z_]", "_", str(col))
    if col and col[0].isdigit():
        col = f"c_{col}"
    return col


def export_cleaned_csv(df):
    path = os.path.join(EXPORT_DIR, "cleaned_dataset.csv")
    df.to_csv(path, index=False)
    return path


def export_r_compatible_csv(df):
    """R read.csv-friendly: syntactically valid column names, no index."""
    r_df = df.copy()
    r_df.columns = [_safe_colname(c) for c in r_df.columns]
    path = os.path.join(EXPORT_DIR, "spine_data_for_R.csv")
    r_df.to_csv(path, index=False, na_rep="NA")
    return path


def export_bi_csv(df):
    """Tableau / Power BI friendly flat extract: clean headers, UTF-8, no index."""
    bi_df = df.copy()
    bi_df.columns = [_safe_colname(c) for c in bi_df.columns]
    path = os.path.join(EXPORT_DIR, "spine_data_for_BI.csv")
    bi_df.to_csv(path, index=False, encoding="utf-8")
    return path
