"""
Flask routes: page views (Stitch UI templates) + JSON API endpoints.
Frontend/vanilla JS calls the /api/* endpoints and renders results into
the existing Stitch dashboard markup - the API layer is intentionally
separated from data_processing / sql_engine / eda / ml_model / exporter.
"""
import os

from flask import Blueprint, jsonify, render_template, request, send_file

from . import data_processing, eda, exporter, ml_model, risk_analysis, sql_engine
from .data_store import store

bp = Blueprint("main", __name__)

SAMPLE_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sample_spine_data.csv")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "uploads")


# ---------------------------------------------------------------- pages ---
@bp.route("/")
def page_dataset_upload():
    return render_template("dataset_upload.html", active="dataset-upload")


@bp.route("/data-overview")
def page_data_overview():
    return render_template("data_overview.html", active="data-overview")


@bp.route("/eda-dashboard")
def page_eda_dashboard():
    return render_template("eda_dashboard.html", active="eda-dashboard")


@bp.route("/sql-insights")
def page_sql_insights():
    return render_template("sql_insights.html", active="sql-insights")


@bp.route("/risk-analysis")
def page_risk_analysis():
    return render_template("risk_analysis.html", active="risk-analysis")


@bp.route("/insights")
def page_insights():
    return render_template("insights.html", active="insights")


@bp.route("/export")
def page_export():
    return render_template("export.html", active="export")


# ------------------------------------------------------------- helpers ---
def _status():
    return {
        "loaded": store.has_data(),
        "source_name": store.source_name,
        "raw_rows": int(store.raw_df.shape[0]) if store.has_data() else 0,
        "raw_columns": int(store.raw_df.shape[1]) if store.has_data() else 0,
        "cleaned": store.has_clean_data(),
        "clean_rows": int(store.clean_df.shape[0]) if store.has_clean_data() else 0,
    }


def _require_data():
    if not store.has_data():
        return jsonify({"error": "No dataset loaded. Upload a CSV or load the sample dataset first."}), 400
    return None


# ------------------------------------------------------------ ingestion ---
@bp.route("/api/status")
def api_status():
    return jsonify(_status())


@bp.route("/api/upload", methods=["POST"])
def api_upload():
    if "file" not in request.files:
        return jsonify({"error": "No file part in request."}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    try:
        df = data_processing.load_csv(file)
    except Exception as exc:
        return jsonify({"error": f"Could not parse CSV: {exc}"}), 400

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    save_path = os.path.join(UPLOAD_DIR, file.filename)
    df.to_csv(save_path, index=False)

    with store.lock:
        store.raw_df = df
        store.clean_df = None
        store.source_name = file.filename
        store.cleaning_log = []
        store.model_results = None

    sql_engine.store_dataframe(df, "patients_raw")

    return jsonify({"message": "Dataset uploaded.", **_status(), "preview": data_processing.dataset_preview(df)})


@bp.route("/api/load-sample", methods=["POST"])
def api_load_sample():
    try:
        df = data_processing.load_csv(SAMPLE_CSV_PATH)
    except Exception as exc:
        return jsonify({"error": f"Could not load sample dataset: {exc}"}), 500

    with store.lock:
        store.raw_df = df
        store.clean_df = None
        store.source_name = "sample_spine_data.csv"
        store.cleaning_log = []
        store.model_results = None

    sql_engine.store_dataframe(df, "patients_raw")

    return jsonify({"message": "Sample dataset loaded.", **_status(), "preview": data_processing.dataset_preview(df)})


@bp.route("/api/preview")
def api_preview():
    err = _require_data()
    if err:
        return err
    return jsonify(data_processing.dataset_preview(store.active_df()))


# ------------------------------------------------------------ overview ---
@bp.route("/api/overview")
def api_overview():
    err = _require_data()
    if err:
        return err
    df = store.active_df()
    return jsonify(
        {
            "preview": data_processing.dataset_preview(df, n=15),
            "dtypes": data_processing.dtype_report(df),
            "missing": data_processing.missing_value_report(df),
            "duplicates": data_processing.duplicate_report(df),
            "status": _status(),
        }
    )


@bp.route("/api/clean", methods=["POST"])
def api_clean():
    err = _require_data()
    if err:
        return err
    cleaned, log = data_processing.clean_dataset(store.raw_df)
    with store.lock:
        store.clean_df = cleaned
        store.cleaning_log = log
        store.model_results = None
    sql_engine.store_dataframe(cleaned, "patients")
    return jsonify(
        {
            "message": "Cleaning pipeline complete.",
            "log": log,
            "preview": data_processing.dataset_preview(cleaned),
            "status": _status(),
        }
    )


# ---------------------------------------------------------------- EDA ---
@bp.route("/api/eda/stats")
def api_eda_stats():
    err = _require_data()
    if err:
        return err
    df = store.active_df()
    return jsonify(
        {
            "descriptive_statistics": eda.descriptive_statistics(df),
            "outliers": eda.outlier_report(df),
        }
    )


@bp.route("/api/eda/correlation")
def api_eda_correlation():
    err = _require_data()
    if err:
        return err
    df = store.active_df()
    return jsonify(
        {
            "matrix": eda.correlation_matrix(df),
            "heatmap_png": eda.correlation_heatmap_png(df),
        }
    )


@bp.route("/api/eda/charts")
def api_eda_charts():
    err = _require_data()
    if err:
        return err
    df = store.active_df()
    category_col = request.args.get("category_col", "risk_category")
    if category_col not in df.columns:
        category_col = None
    return jsonify(eda.eda_charts_bundle(df, category_col=category_col))


@bp.route("/api/eda/chart")
def api_eda_single_chart():
    """On-demand single chart, e.g. /api/eda/chart?type=histogram&column=bmi"""
    err = _require_data()
    if err:
        return err
    df = store.active_df()
    chart_type = request.args.get("type", "histogram")
    column = request.args.get("column")
    group_by = request.args.get("group_by")
    x = request.args.get("x")
    y = request.args.get("y")

    image = None
    if chart_type == "histogram" and column:
        image = eda.histogram_png(df, column)
    elif chart_type == "boxplot" and column:
        image = eda.boxplot_png(df, column, group_by=group_by)
    elif chart_type == "bar" and column:
        image = eda.bar_chart_png(df, column)
    elif chart_type == "scatter" and x and y:
        image = eda.scatter_png(df, x, y, hue=group_by)
    else:
        return jsonify({"error": "Invalid chart request."}), 400

    if image is None:
        return jsonify({"error": "Could not generate chart for the given column(s)."}), 400
    return jsonify({"image": image})


# ---------------------------------------------------------------- SQL ---
@bp.route("/api/sql/examples")
def api_sql_examples():
    err = _require_data()
    if err:
        return err
    table = "patients" if store.has_clean_data() else "patients_raw"
    return jsonify({"table": table, "examples": sql_engine.example_queries(table)})


@bp.route("/api/sql/query", methods=["POST"])
def api_sql_query():
    err = _require_data()
    if err:
        return err
    payload = request.get_json(silent=True) or {}
    sql = payload.get("sql", "")
    if not sql.strip():
        return jsonify({"error": "Empty SQL query."}), 400
    try:
        table = "patients" if store.has_clean_data() else "patients_raw"
        result = sql_engine.run_query(sql, table_name=table)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


# ------------------------------------------------------------- risk ---
@bp.route("/api/risk/distribution")
def api_risk_distribution():
    err = _require_data()
    if err:
        return err
    return jsonify(risk_analysis.risk_distribution(store.active_df()))


@bp.route("/api/risk/aggregate")
def api_risk_aggregate():
    err = _require_data()
    if err:
        return err
    group_col = request.args.get("group_col", "activity_level")
    agg_col = request.args.get("agg_col")
    return jsonify(risk_analysis.aggregate_by(store.active_df(), group_col, agg_col))


@bp.route("/api/risk/recommendations")
def api_risk_recommendations():
    err = _require_data()
    if err:
        return err
    return jsonify({"recommendations": risk_analysis.risk_recommendations(store.active_df())})


# --------------------------------------------------------------- model ---
@bp.route("/api/model/train", methods=["POST"])
def api_model_train():
    err = _require_data()
    if err:
        return err
    df = store.active_df()
    try:
        results = ml_model.train_and_compare(df)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    with store.lock:
        store.model_results = results
    return jsonify(results)


@bp.route("/api/model/results")
def api_model_results():
    if store.model_results is None:
        return jsonify({"trained": False})
    return jsonify({"trained": True, **store.model_results})


# -------------------------------------------------------------- export ---
@bp.route("/api/export/cleaned-csv")
def api_export_cleaned():
    err = _require_data()
    if err:
        return err
    path = exporter.export_cleaned_csv(store.active_df())
    return send_file(path, as_attachment=True, download_name="cleaned_dataset.csv")


@bp.route("/api/export/r-csv")
def api_export_r():
    err = _require_data()
    if err:
        return err
    path = exporter.export_r_compatible_csv(store.active_df())
    return send_file(path, as_attachment=True, download_name="spine_data_for_R.csv")


@bp.route("/api/export/bi-csv")
def api_export_bi():
    err = _require_data()
    if err:
        return err
    path = exporter.export_bi_csv(store.active_df())
    return send_file(path, as_attachment=True, download_name="spine_data_for_BI.csv")


@bp.route("/api/export/summary")
def api_export_summary():
    """A JSON analytical summary bundling the headline numbers from every
    stage of the pipeline - useful as a one-shot report payload."""
    err = _require_data()
    if err:
        return err
    df = store.active_df()
    summary = {
        "status": _status(),
        "cleaning_log": store.cleaning_log,
        "missing": data_processing.missing_value_report(df),
        "duplicates": data_processing.duplicate_report(df),
        "descriptive_statistics": eda.descriptive_statistics(df),
        "risk_distribution": risk_analysis.risk_distribution(df),
        "model_results": store.model_results,
    }
    return jsonify(summary)
