# Week 12 作業 — Dataset Hygiene & Stroop Dashboard

## 執行方式

```bash
pip install pandas numpy matplotlib streamlit
streamlit run app.py
```

Dashboard 會直接讀取 `./data/messy_stroop_homework.csv`。  
若需要重新生成資料集：`cd data && python generate_messy_stroop_homework.py`

---

## 資料來源

**資料集**：`./data/messy_stroop_homework.csv`，以 `seed=2026` 生成，n = 243 列（含 3 列刻意注入的重複列）。

**文獻引用**：

> Ménétré, E., & Laganaro, M. (2023). The temporal dynamics of the Stroop effect from childhood to young and older adulthood. *PLOS ONE*, *18*(3), e0256003. https://doi.org/10.1371/journal.pone.0256003

---

## 三條最重要的 Cleaning 決定

1. **`rt_ms` 範圍限定為 200–3000 ms** — 下限 200 ms 取自 Ménétré & Laganaro (2023, Sec. 2.4) 的絕對生理閾值（來源：文獻）；上限 3000 ms 採課堂 demo 的保守範圍，因文獻的 SD-based 上限（1074.5 ms）依賴該研究樣本的分佈，不可直接移植到本資料集（來源：文獻 + 生成器第 43 行）。

2. **`condition` 標準化為 2 個 level** — 生成器在第 40–42 行與第 89–91 行注入了 6 種字面變體（含尾端空白、大小寫不一致、縮寫 "con" / "incong."），以 `strip()` → `lower()` → `replace()` map 三步驟還原為標準的 congruent / incongruent（來源：生成器）。

3. **`rt_ms` 四種 sentinel 值替換為 `NaN`** — 兩種字串 sentinel（`"missing"`、`"--"`）與兩種數值 sentinel（`-1`、`9999`）共影響 21 列，分別由生成器第 59–84 行確認語意，並以原始資料的 `value_counts()` 觀察驗證（來源：生成器 + 觀察）。

---

## 為什麼 `outlier_sd` 放在 `analyse()` 而非 `clean()`

`clean()` 處理的是客觀的資料錯誤——dtype 錯誤、sentinel 值、重複列——這些問題不論研究問題為何都應該修正。Outlier 門檻則是**分析層的研究決策**：不同的研究問題、敏感度分析，或不同的引用文獻，都可能合理地採用 ±2 SD、±3 SD 或 ±2.5 SD，而每種選擇都會得出不同的 Stroop effect 估計值。若把門檻寫死在 `clean()` 裡，所有後續分析都會被隱性地鎖定在同一個閾值，也無從審視不同選擇對結論的影響。將它作為顯式參數放在 `analyse(df, *, outlier_sd=3.0)` 中，既維持了 cleaning / analysis 的邊界紀律，也讓 dashboard 可以透過 slider 互動式地探索不同閾值的效果。
