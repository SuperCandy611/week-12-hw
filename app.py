"""
app.py — Week 12 作業 Part B: Stroop Experiment Dashboard

執行：
    streamlit run app.py
"""

import time

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

matplotlib.use("Agg")  # 避免 Streamlit 中觸發 GUI backend 警告

DATA_PATH = "./data/messy_stroop_homework.csv"

# ──────────────────────────────────────────────────────────────────────────────
# Data pipeline（邏輯與 report.ipynb A.4 clean() 完全相同）
# ──────────────────────────────────────────────────────────────────────────────

def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """Pure cleaning function — mirrors report.ipynb A.4."""
    df = df.copy()
    # Step 1: 去除重複列（生成器第 108–110 行造成的 3 列重複）
    df = df.drop_duplicates()
    # Step 2: 標準化 condition → 2 個 level
    df["condition"] = df["condition"].str.strip().str.lower()
    df["condition"] = df["condition"].replace(
        {"con": "congruent", "incong.": "incongruent"}
    )
    df["condition"] = df["condition"].astype("category")
    # Steps 3–5: rt_ms dtype + sentinel + 範圍過濾 200–3000 ms
    df["rt_ms"] = pd.to_numeric(df["rt_ms"], errors="coerce")
    df["rt_ms"] = df["rt_ms"].replace({-1: np.nan, 9999: np.nan})
    df = df.dropna(subset=["rt_ms"])
    df = df[df["rt_ms"].between(200, 3000)]
    # Step 6: accuracy 字串 → int
    df["accuracy"] = df["accuracy"].replace({"True": 1, "False": 0})
    df["accuracy"] = pd.to_numeric(df["accuracy"], errors="coerce").astype("Int64")
    # Step 7: age sentinel → NaN
    df["age"] = df["age"].replace({-1: np.nan, 888: np.nan})
    return df


# ──────────────────────────────────────────────────────────────────────────────
# B.1 — Cached data loaders
# ──────────────────────────────────────────────────────────────────────────────

# ttl=600：CSV 在正常使用期間不會改變，10 分鐘後過期確保重跑生成器後能拿到新檔案
# show_spinner：明確告知使用者目前執行到哪個階段，改善 UX
@st.cache_data(ttl=600, show_spinner="Loading raw data…")
def load_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


# max_entries=1：整個 app 只有一個 dataset，不需要快取多個 entry
# clean() 是 deterministic function（相同輸入→相同輸出），適合被 cache
@st.cache_data(max_entries=1, show_spinner="Cleaning data…")
def get_clean_data(path: str) -> pd.DataFrame:
    raw = load_data(path)
    return _clean(raw)


# ──────────────────────────────────────────────────────────────────────────────
# Analysis helper（outlier_sd 放這裡而非 clean()，理由見 report.ipynb A.6）
# ──────────────────────────────────────────────────────────────────────────────

def compute_stroop(df: pd.DataFrame, outlier_sd: float = 3.0):
    """計算 Stroop effect；資料不足時回傳 None。"""
    if df.empty or df["condition"].nunique() < 2:
        return None
    mu, sigma = df["rt_ms"].mean(), df["rt_ms"].std()
    df = df[df["rt_ms"].between(mu - outlier_sd * sigma, mu + outlier_sd * sigma)]
    grp = df.groupby("condition", observed=True)["rt_ms"].agg(["mean", "std", "count"])
    if "congruent" not in grp.index or "incongruent" not in grp.index:
        return None
    mean_c = grp.loc["congruent",   "mean"]
    mean_i = grp.loc["incongruent", "mean"]
    return {
        "mean_cong":     mean_c,
        "sd_cong":       grp.loc["congruent",   "std"],
        "n_cong":        int(grp.loc["congruent",   "count"]),
        "mean_incong":   mean_i,
        "sd_incong":     grp.loc["incongruent", "std"],
        "n_incong":      int(grp.loc["incongruent", "count"]),
        "stroop_effect": mean_i - mean_c,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Stroop Dashboard",
    layout="wide",
)

# ──────────────────────────────────────────────────────────────────────────────
# Load & clean（計時以偵測 cache 命中）
# ──────────────────────────────────────────────────────────────────────────────

t0 = time.perf_counter()
df_clean = get_clean_data(DATA_PATH)
elapsed_ms = (time.perf_counter() - t0) * 1000

# ──────────────────────────────────────────────────────────────────────────────
# Sidebar — B.2 篩選器
# ──────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("Filters")

    # Widget 1 — subject_id multiselect
    all_subjects = sorted(df_clean["subject_id"].unique().tolist())
    selected_subjects = st.multiselect(
        "Subject ID",
        options=all_subjects,
        default=all_subjects,
    )

    # Widget 2 — rt_ms range slider
    rt_min = float(df_clean["rt_ms"].min())
    rt_max = float(df_clean["rt_ms"].max())
    rt_range = st.slider(
        "RT range (ms)",
        min_value=rt_min,
        max_value=rt_max,
        value=(rt_min, rt_max),
        step=10.0,
    )

    # Widget 3 — outlier_sd（分析層參數，不在 clean() 中）
    outlier_sd = st.slider(
        "Outlier threshold (± SD)",
        min_value=1.5,
        max_value=4.0,
        value=3.0,
        step=0.5,
        help="Applied in analyse() — not in clean(). See report.ipynb A.6.",
    )

    st.divider()

    # 加分：cache 命中偵測
    st.markdown("**Cache status**")
    st.metric("Load time", f"{elapsed_ms:.1f} ms")
    # get_clean_data 從 cache 回傳時幾乎為 0 ms；首次載入通常 > 50 ms
    if elapsed_ms < 30:
        st.success("Cache HIT")
    else:
        st.info("Cache MISS (first load or expired)")

    # 加分：Clear cache 按鈕
    if st.button("Clear cache", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# Boolean mask — sidebar 值反映到主畫面
# ──────────────────────────────────────────────────────────────────────────────

mask = (
    df_clean["subject_id"].isin(selected_subjects)
    & df_clean["rt_ms"].between(rt_range[0], rt_range[1])
)
df_filtered = df_clean[mask]

# ──────────────────────────────────────────────────────────────────────────────
# Main content
# ──────────────────────────────────────────────────────────────────────────────

st.title("Stroop Experiment Dashboard")
st.caption(
    f"Dataset: `{DATA_PATH}` · "
    f"After cleaning: **{len(df_clean)}** trials · "
    f"After filtering: **{len(df_filtered)}** trials"
)

results = compute_stroop(df_filtered, outlier_sd=outlier_sd)

# ── B.3 Block 1: KPI metrics ──────────────────────────────────────────────────

st.subheader("Key Metrics")

if results is None:
    st.warning("Not enough data to compute Stroop effect. Adjust sidebar filters.")
else:
    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "N Trials",
        results["n_cong"] + results["n_incong"],
        help="After outlier filter (±SD threshold above)",
    )
    col2.metric(
        "Mean RT — Congruent",
        f"{results['mean_cong']:.1f} ms",
        help=f"n = {results['n_cong']},  SD = {results['sd_cong']:.1f} ms",
    )
    col3.metric(
        "Mean RT — Incongruent",
        f"{results['mean_incong']:.1f} ms",
        delta=f"{results['stroop_effect']:+.1f} ms vs congruent",
        help=f"n = {results['n_incong']},  SD = {results['sd_incong']:.1f} ms",
    )
    col4.metric(
        "Stroop Effect",
        f"{results['stroop_effect']:.1f} ms",
        help="incongruent mean − congruent mean",
    )

# ── B.3 Block 2: Chart ────────────────────────────────────────────────────────

st.subheader("Mean RT by Condition × Subject")

if df_filtered.empty:
    st.warning("No data to plot.")
else:
    grp = (
        df_filtered.groupby(["subject_id", "condition"], observed=True)["rt_ms"]
        .mean()
        .reset_index()
    )
    pivot = grp.pivot(index="subject_id", columns="condition", values="rt_ms")

    fig, ax = plt.subplots(figsize=(8, 4))
    pivot.plot(
        kind="bar",
        ax=ax,
        color=[
            "steelblue" if c == "congruent" else "salmon"
            for c in pivot.columns
        ],
        edgecolor="black",
        alpha=0.85,
    )
    ax.set_xlabel("Subject ID")
    ax.set_ylabel("Mean RT (ms)")
    ax.set_title(f"Mean RT per Subject  (outlier_sd = ±{outlier_sd} SD)")
    ax.legend(title="Condition")
    ax.tick_params(axis="x", rotation=0)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

# ── B.3 Block 3: Data table ───────────────────────────────────────────────────

st.subheader("Data")

tab1, tab2 = st.tabs(["Group summary", "Raw rows (first 50)"])

with tab1:
    if df_filtered.empty:
        st.warning("No data.")
    else:
        summary = (
            df_filtered.groupby("condition", observed=True)["rt_ms"]
            .agg(["count", "mean", "std", "min", "max"])
            .rename(columns={
                "count": "N", "mean": "Mean RT (ms)",
                "std": "SD", "min": "Min", "max": "Max",
            })
            .round(1)
        )
        st.dataframe(summary, use_container_width=True)

with tab2:
    st.dataframe(df_filtered.head(50), use_container_width=True)
