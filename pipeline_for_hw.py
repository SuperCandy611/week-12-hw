"""Demo 3: Data Analysis Pipeline — load → describe → fix → re-describe → analyse.

對應 Week 12 slides 25 (pipeline diagram), 28–37 (descriptive stats,
observation-driven fixing, end-to-end Stroop demo)。

執行：
    python pipeline.py        # 純命令列版本
    # 或在 notebook 中 import 與測試

這支檔案故意把流程拆成 4 個 pure functions：
    load_raw    — I/O only
    describe    — 健康檢查報表
    clean       — 不可爭議的修補
    analyse     — 可爭議閾值放這裡（outlier_sd），暴露成參數

學生 final project 可以照這個結構組織自己的 pipeline。
"""

from pathlib import Path
import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data" / "messy_stroop.csv"


# ---------------------------------------------------------------
# 1. load — I/O only
# ---------------------------------------------------------------
def load_raw(path: Path = DATA) -> pd.DataFrame:
    """純 I/O，不做任何 transformation。"""
    return pd.read_csv(path)


# ---------------------------------------------------------------
# 2 + 3. describe — 健康檢查報表
# ---------------------------------------------------------------
def describe(df: pd.DataFrame) -> dict:
    """產生結構化的資料品質報表 — 不修改 df。"""
    report = {
        "shape":   df.shape,
        "dtypes":  df.dtypes.astype(str).to_dict(),
        "n_null":  df.isnull().sum().to_dict(),
    }
    # numeric describe
    num = df.select_dtypes(include="number")
    if len(num.columns):
        report["numeric_summary"] = num.describe().round(2).to_dict()
    # categorical value_counts
    cat_levels = {}
    for col in df.select_dtypes(include="object"):
        cat_levels[col] = df[col].value_counts(dropna=False).to_dict()
    report["cat_levels"] = cat_levels
    return report


def print_report(report: dict, title: str = "Report") -> None:
    """以易讀格式印出 describe() 的結果。"""
    print(f"\n{'='*60}\n{title}\n{'='*60}")
    print(f"shape: {report['shape']}")
    print(f"dtypes: {report['dtypes']}")
    print(f"n_null: {report['n_null']}")
    if "numeric_summary" in report:
        print(f"numeric_summary:")
        for col, stats in report["numeric_summary"].items():
            print(f"  {col}: {stats}")
    print(f"cat_levels:")
    for col, levels in report["cat_levels"].items():
        print(f"  {col}: {levels}")


# ---------------------------------------------------------------
# 4. clean — 不可爭議的修補 (pure function, testable)
# ---------------------------------------------------------------
def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Stroop dataset 的清理函式。

    每一步對應一個 descriptive statistics 的觀察：

    觀察 → 動作 → 代價
    --------------------------------------------------------------
    1. rt_ms dtype 是 object（含 "NA"）
       → pd.to_numeric(errors="coerce")
       → 代價：無法解析的值悄悄變 NaN
    2. rt_ms 含 99999 sentinel
       → between(150, 3000) filter
       → 代價：範圍選錯會剔除真實的極端 RT
    3. age 有 -999 sentinel
       → replace({-999: np.nan})
       → 代價：後續 age-based 分析會少 n
    4. condition 大小寫不一致（4 levels 但實際 2 個）
       → str.lower() + replace({"incong": "incongruent"})
       → 代價：合併不該合的 level（這裡確認過安全）
    """
    df = df.copy()
    # 1) rt_ms type fix
    df["rt_ms"] = pd.to_numeric(df["rt_ms"], errors="coerce")
    # 2) rt_ms physically implausible
    df = df[df["rt_ms"].between(150, 3000)]
    # 3) age sentinel
    df["age"] = df["age"].replace({-999: np.nan})
    # 4) condition recode
    df["condition"] = (
        df["condition"].str.lower().replace({"incong": "incongruent"})
    )
    return df


# ---------------------------------------------------------------
# 5. analyse — 可爭議閾值暴露成參數
# ---------------------------------------------------------------
def analyse(df: pd.DataFrame, *, outlier_sd: float = 3.0) -> pd.DataFrame:
    """計算 condition × subject 的 mean RT 與 Stroop effect。

    outlier_sd 為可爭議閾值（不同研究者可能選不同值）—
    把它暴露成參數而非寫死，方便 sensitivity analysis 與 pre-registration。
    """
    df = df.copy()
    # subject-wise outlier rejection（mean ± SD × outlier_sd）
    grouped = df.groupby("subject_id")["rt_ms"]
    means, sds = grouped.transform("mean"), grouped.transform("std")
    keep = (df["rt_ms"] - means).abs() <= outlier_sd * sds
    df = df[keep]
    # condition mean
    summary = (df.groupby("condition")["rt_ms"]
                 .agg(["mean", "std", "count"])
                 .round(1))
    # Stroop effect (incongruent − congruent)
    if {"congruent", "incongruent"}.issubset(summary.index):
        effect = (summary.loc["incongruent", "mean"]
                  - summary.loc["congruent", "mean"])
        summary.attrs["stroop_effect_ms"] = round(effect, 1)
    return summary


# ---------------------------------------------------------------
# Main — demonstrate the full pipeline
# ---------------------------------------------------------------
if __name__ == "__main__":
    raw = load_raw()

    print_report(describe(raw), "BEFORE cleaning")

    cleaned = clean(raw)
    print_report(describe(cleaned), "AFTER cleaning (re-describe)")

    print("\n" + "="*60)
    print("ANALYSE")
    print("="*60)
    result = analyse(cleaned, outlier_sd=3.0)
    print(result)
    if "stroop_effect_ms" in result.attrs:
        print(f"\nStroop effect (incong - cong) = "
              f"{result.attrs['stroop_effect_ms']} ms")
