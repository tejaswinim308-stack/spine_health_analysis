"""
Data Scientist layer, part 2: the optional ML component. Trains and
compares two classifiers (Logistic Regression, Random Forest) to predict
the analytical 'risk_category' label from engineered features, and reports
offline-validation metrics. This is a supporting component of the analytics
platform, not a diagnostic system - outputs are framed as 'risk assessment'
/ 'pattern analysis', never as medical diagnosis.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

from . import data_processing

TARGET_COL = "risk_category"


def _prepare_xy(df, target_col=TARGET_COL):
    work, feature_notes = data_processing.engineer_features(df)

    if target_col not in work.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataset.")

    work = work.dropna(subset=[target_col])
    y_raw = work[target_col].astype(str)

    drop_cols = [target_col]
    for c in work.columns:
        if pd.api.types.is_object_dtype(work[c]) or pd.api.types.is_string_dtype(work[c]):
            if work[c].nunique() > 0.9 * len(work):  # looks like an identifier
                drop_cols.append(c)
    X = work.drop(columns=[c for c in drop_cols if c in work.columns])

    # One-hot encode remaining categorical columns
    X = pd.get_dummies(X, drop_first=False)
    X = X.fillna(X.median(numeric_only=True))
    X = X.loc[:, X.nunique() > 1]  # drop constant columns

    le = LabelEncoder()
    y = le.fit_transform(y_raw)

    return X, y, le, feature_notes


def train_and_compare(df, target_col=TARGET_COL, test_size=0.25, random_state=42):
    X, y, label_encoder, feature_notes = _prepare_xy(df, target_col)

    if len(np.unique(y)) < 2:
        raise ValueError("Target column needs at least two classes to train a classifier.")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    models = {
        "Logistic Regression": LogisticRegression(max_iter=2000),
        "Random Forest": RandomForestClassifier(n_estimators=300, max_depth=8, random_state=random_state),
    }

    results = {}
    class_names = list(label_encoder.classes_)

    for name, model in models.items():
        if name == "Logistic Regression":
            model.fit(X_train_scaled, y_train)
            y_pred = model.predict(X_test_scaled)
            y_proba = model.predict_proba(X_test_scaled)
        else:
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            y_proba = model.predict_proba(X_test)

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, average="weighted", zero_division=0)
        rec = recall_score(y_test, y_pred, average="weighted", zero_division=0)
        f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)

        try:
            if len(class_names) == 2:
                auc = roc_auc_score(y_test, y_proba[:, 1])
            else:
                auc = roc_auc_score(y_test, y_proba, multi_class="ovr", average="weighted")
        except ValueError:
            auc = None

        cm = confusion_matrix(y_test, y_pred, labels=list(range(len(class_names))))

        importance = None
        if name == "Random Forest":
            importance = sorted(
                (
                    {"feature": f, "importance": round(float(imp), 4)}
                    for f, imp in zip(X.columns, model.feature_importances_)
                ),
                key=lambda r: -r["importance"],
            )
        elif name == "Logistic Regression":
            coefs = np.abs(model.coef_).mean(axis=0)
            total = coefs.sum() or 1.0
            importance = sorted(
                (
                    {"feature": f, "importance": round(float(c) / float(total), 4)}
                    for f, c in zip(X.columns, coefs)
                ),
                key=lambda r: -r["importance"],
            )

        results[name] = {
            "accuracy": round(float(acc), 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
            "roc_auc": round(float(auc), 4) if auc is not None else None,
            "confusion_matrix": cm.tolist(),
            "class_names": class_names,
            "feature_importance": importance[:12],
        }

    best_model = max(results, key=lambda k: results[k]["f1_score"])

    return {
        "target_col": target_col,
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "n_features": int(X.shape[1]),
        "feature_engineering_notes": feature_notes,
        "class_distribution": {
            cls: int((y == i).sum()) for i, cls in enumerate(class_names)
        },
        "models": results,
        "best_model": best_model,
    }
