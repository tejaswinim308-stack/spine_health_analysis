"""
Generates a synthetic 'spine_biomechanics_sample.csv' dataset for the
Spine Health Analytics & Risk Assessment Platform.

The feature set is modeled on the well-known biomechanical vertebral-column
research (pelvic incidence, pelvic tilt, lumbar lordosis angle, sacral slope,
pelvic radius, degree of spondylolisthesis) plus a handful of lifestyle /
clinical-intake style fields, and a derived multi-class RISK category
(Low / Moderate / High) used as the analytical target.

This is SYNTHETIC data generated for demonstration of a data analytics /
data science pipeline. It is NOT real patient data and must never be
described as a diagnostic tool.

Run: python generate_sample.py
"""
import numpy as np
import pandas as pd

np.random.seed(42)

N = 850

# --- Core biomechanical features (correlated, roughly realistic ranges) ---
pelvic_incidence = np.random.normal(60, 17, N).clip(15, 130)
pelvic_tilt = (0.4 * pelvic_incidence + np.random.normal(5, 8, N)).clip(-10, 55)
sacral_slope = pelvic_incidence - pelvic_tilt + np.random.normal(0, 4, N)
sacral_slope = sacral_slope.clip(10, 100)
lumbar_lordosis_angle = (0.6 * pelvic_incidence + np.random.normal(10, 10, N)).clip(10, 130)
pelvic_radius = np.random.normal(118, 13, N).clip(70, 165)

# degree_spondylolisthesis: heavy-tailed, driven partly by pelvic incidence
base_spondy = np.random.exponential(scale=12, size=N) - 5
spondy_bump = np.where(pelvic_incidence > 75, np.random.exponential(25, N), 0)
degree_spondylolisthesis = (base_spondy + spondy_bump + np.random.normal(0, 5, N)).clip(-10, 300)

# --- Patient / lifestyle attributes ---
age = np.random.normal(46, 15, N).clip(18, 88).round().astype(int)
bmi = np.random.normal(26, 4.5, N).clip(16, 45).round(1)
activity_level = np.random.choice(
    ["Sedentary", "Moderate", "Active"], size=N, p=[0.38, 0.42, 0.20]
)
smoking_status = np.random.choice(["No", "Yes"], size=N, p=[0.78, 0.22])
occupation_load = np.random.choice(
    ["Light", "Moderate", "Heavy"], size=N, p=[0.45, 0.35, 0.20]
)

# pain score influenced by spondylolisthesis, bmi, activity
pain_base = (
    0.04 * degree_spondylolisthesis
    + 0.08 * (bmi - 25)
    + np.where(activity_level == "Sedentary", 1.2, 0)
    + np.where(occupation_load == "Heavy", 1.0, 0)
    + np.random.normal(3, 1.8, N)
)
pain_score = np.clip(pain_base, 0, 10).round(1)

# --- Derived RISK CATEGORY target (rule + noise, mirrors a clinical rubric) ---
risk_score = (
    0.35 * (degree_spondylolisthesis / 10)
    + 0.25 * (pain_score)
    + 0.15 * (bmi - 22).clip(min=0)
    + np.where(smoking_status == "Yes", 3, 0)
    + np.where(activity_level == "Sedentary", 2, 0)
    + np.random.normal(0, 3, N)
)

risk_category = pd.qcut(
    risk_score,
    q=[0, 0.45, 0.8, 1.0],
    labels=["Low", "Moderate", "High"],
)

df = pd.DataFrame(
    {
        "patient_id": [f"SP{100000+i}" for i in range(N)],
        "age": age,
        "bmi": bmi,
        "pelvic_incidence": pelvic_incidence.round(2),
        "pelvic_tilt": pelvic_tilt.round(2),
        "lumbar_lordosis_angle": lumbar_lordosis_angle.round(2),
        "sacral_slope": sacral_slope.round(2),
        "pelvic_radius": pelvic_radius.round(2),
        "degree_spondylolisthesis": degree_spondylolisthesis.round(2),
        "activity_level": activity_level,
        "occupation_load": occupation_load,
        "smoking_status": smoking_status,
        "pain_score": pain_score,
        "risk_category": risk_category.astype(str),
    }
)

# --- Inject realistic data-quality issues for the cleaning pipeline to catch ---
rng = np.random.default_rng(7)

# Missing values scattered across several columns
for col, frac in [
    ("bmi", 0.03),
    ("pelvic_radius", 0.025),
    ("pain_score", 0.02),
    ("occupation_load", 0.015),
    ("smoking_status", 0.01),
]:
    idx = rng.choice(N, size=int(N * frac), replace=False)
    df.loc[idx, col] = np.nan

# A handful of exact duplicate rows
dup_idx = rng.choice(N, size=12, replace=False)
df = pd.concat([df, df.loc[dup_idx]], ignore_index=True)

# Shuffle
df = df.sample(frac=1, random_state=1).reset_index(drop=True)

df.to_csv("sample_spine_data.csv", index=False)
print(f"Wrote sample_spine_data.csv with {len(df)} rows, {df.shape[1]} columns")
print(df.isna().sum())
