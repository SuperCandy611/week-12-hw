# Week 12 作業 — Dataset Hygiene & Caching Dashboard

> **課程**：NS5116 電腦硬體與程式語言在行為科學實驗與大數據分析之應用
> **指派日期**：2026-05-14
> **繳交期限**：2026-05-20 (Wed) 23:59，Week 13 上課前
> **配分**：本週課程作業總分 100%

---

## 1. 作業目標 (Learning Goals)

把本週的兩個核心觀念**親自走過一次**：

1. **Data analysis pipeline** — load → inspect → describe → fix → re-describe → analyse，每個 cleaning 動作都對應到 descriptive statistics 中觀察到的具體現象。
2. **Streamlit caching** — 在 dashboard 中正確使用 `@st.cache_data`，並能解釋為什麼這樣放、用什麼參數。

最終成果是一份**有可讀性的 dataset hygiene 報告**加上一個**功能性的 Streamlit dashboard**。

---

## 2. 指定資料集 (Dataset)

**檔案**：`./data/messy_stroop_homework.csv` (n ≈ 240 trials，含若干重複 row)

如果遺失，可在 `./data/` 執行 `python generate_messy_stroop_homework.py`
重新生成（`seed=2026`）。

> ⚠️ **注意**：本作業使用的資料集 (`messy_stroop_homework.csv`) **與課堂 demo 用的
> `messy_stroop.csv` 不同**。**「髒」的原則一致**（dtype 錯誤、sentinel value、
> categorical 不一致、numeric 超出範圍 ⋯⋯），但**具體的 sentinel 數值、
> 字串標記、欄位編碼方式、甚至「髒」的種類數量都不同**。
>
> ✗ 直接複製 demo `pipeline.py::clean` 的程式碼**不會通過** — 例如 demo 用
> `replace({-999: np.nan})` 處理 age，但本資料集的 age sentinel 不是 -999。
>
> ✓ 套用 demo 教的**原則**（先 to_numeric、replace sentinel、between range filter
> ……）才會通過。這正是本作業要訓練的能力：**從具體案例抽象出原則**，再應用到
> 新案例。

### 2.1 重要：欄位資訊是「線索」不是「答案」

下面這個表是 **教師對欄位的初步說明**，但它**不是規則的最終來源**。在真實研究情境裡，這個表通常來自實驗者口頭描述、舊版 codebook、或 PI 寄來的 email — 都可能不完整或過時。

> **你的責任之一就是不要照單全收這個表，而要去調查並驗證它。** 詳細做法見 Part A.0。

### 2.2 教師的初步欄位描述

| 欄位 | 教師說的「預期意義」 | 教師說的「預期型別」 |
|------|----------|----------|
| `trial_id` | trial 編號 | 整數，每個 trial 唯一 |
| `subject_id` | 受試者編號 | 整數 |
| `condition` | Stroop 條件 | 文字 (2 levels) |
| `rt_ms` | 反應時間 | 數值，毫秒 |
| `accuracy` | 正確與否 | 0 / 1 |
| `age` | 年齡 | 數值 |

⚠️ 表中**故意沒有寫合理範圍與 sentinel 值**。這些規則必須由你**從證據中推導出來**（見 A.0）。

> 💡 **比起課堂 demo，本資料集有幾個新增的調查點** — 你會在 A.3 用 descriptive
> statistics 自己發現它們：
>
> - 同欄位可能有**不只一種** sentinel value（同一個欄位混了兩種特殊值）
> - 同欄位可能有**不只一種**「正確值的格式」（例如 0/1 與某種字串混存）
> - `trial_id` 是 row-level unique 嗎？或可能有重複？
> - `condition` 的「不一致」可能比 demo 多一層（不只大小寫）

### 2.3 為什麼用這個 dataset

- 規模小、跑得快
- 真實研究中常見的「髒」樣態都被刻意注入（且**比課堂 demo 多了幾種變化**）
- 內含一個可分析的 **Stroop effect** — cleaning 對了，你應該能在 incongruent 與 congruent 條件間看出 RT 差異（約 70–90 ms 範圍）
- **生成器原始碼公開**（`./data/generate_messy_stroop_homework.py`）— 等於
  是這份資料的「最終 source of truth」，學生可以從它逆推欄位定義與注入的
  問題類型。這就是 A.0「來源 1」要紀錄的對象。

---

## 3. 繳交內容 (Deliverables)

學生需將以下檔案上傳到自己的github，以及佈署到streamlit：

```
https://github.com/<yourrepo>/<yourhw12_repo>
├── report.ipynb       ← Part A — 完整 pipeline 報告
├── app.py             ← Part B — Streamlit dashboard
└── README.md          ← 簡短說明（≤ 1 頁，告訴教師怎麼跑你的東西）

https://<your streamlit>.streamlit.app
```

---

## Part A — Analysis Report (`report.ipynb`)  · 65 分

把 Jupyter notebook 想像成你寫給未來自己（或 reviewer）看的**分析日記**。

### 必須包含的章節

#### A.0 Data Source & Schema Investigation  · 10 分

> **本節是本作業最重要的方法論訓練**。
> 任何資料分析的第一步都是「先搞清楚這份資料是怎麼來的、欄位定義從哪來、規則的根據是什麼」 —
> 而不是直接套用別人給的「合理範圍」。

請以**三個獨立來源交叉驗證**（triangulation）的方式調查並紀錄欄位規則，**每個來源都要在 notebook 中明確引用**：

##### 來源 1 — 生成器原始碼 (Generator)

打開 `./data/generate_messy_stroop_homework.py`，閱讀並紀錄：

1. 各欄位**被生成時**的型別與數值範圍（例如 `rt_ms` 是 `np.random.normal(500, 80, N)` → 期望分佈中心 500、SD 80）
2. **刻意被注入的 messy patterns** — 程式碼中哪幾行造成了 dtype 錯誤、sentinel value、編碼不一致？
3. `seed` 是否固定？同樣 seed 跑兩次會不會得到同一份資料？

> **要交什麼**：在 notebook 中用 markdown 寫一段 200–400 字的「生成器逆向工程紀錄」，並貼出你判定 messy patterns 的關鍵程式行（用 markdown code fence 引用，**不是**截圖）。

##### 來源 2 — 文獻 (Literature)

`rt_ms` 的「合理範圍」不能憑感覺。請在 Google Scholar / PubMed 找 **至少一篇** 已發表的 Stroop 研究，紀錄並引用：

1. 該研究中 RT 的**典型 mean ± SD**
2. 該研究中是否提到 RT outlier rejection 的**門檻**（例如 < 200 ms 被視為猜測、> 2500 ms 被視為走神 — 但實際數字依研究而異，**請以你查到的論文為準**）
3. 該研究的 **Stroop effect 量級**（incongruent − congruent 的差異，常見落在 ~50–100 ms）

> ⚠️ **注意**：課堂 demo `pipeline.py` 用的是 `between(150, 3000)`，
> 與許多文獻採用的較嚴格範圍（如 200–2500）不同。**這是刻意的對照**：
> 課堂選寬鬆範圍是為了 demo 易讀且不損失太多 trial。在 A.0 你可以
> 採用 demo 的範圍、文獻的範圍、或自己折衷 — 重點是**寫清楚你的依據與取捨**。

> **要交什麼**：APA 格式引用 1 篇研究，並用 1–2 句話總結你從中採用的 RT 合理範圍與 outlier rule 的**依據**。
>
> **建議起手關鍵字**：`Stroop reaction time outlier exclusion`、`Stroop effect young adults`、`response time data trimming behavioral`
>
> 💡 推薦起手文獻：
> - MacLeod, C. M. (1991). Half a century of research on the Stroop effect. *Psychological Bulletin*, 109(2), 163–203.
> - Whelan, R. (2008). Effective analysis of reaction time data. *The Psychological Record*, 58(3), 475–482.

##### 來源 3 — 資料本身 (Data-Driven Discovery)

用 `df.describe(include="all")`、`df.dtypes`、`df.isnull().sum()`、`df["col"].value_counts(dropna=False)` 對**未清理**的資料做初步觀察，紀錄：

1. 哪些欄位的 **觀察分佈** 與 來源 1 的生成器宣告**不一致**？（例如：生成器寫 `rt_ms` 是 normal(500, 80)，但你看到的 max = 99999 — 這就是 sentinel 注入的證據）
2. 哪些欄位的 **觀察分佈** 與 來源 2 的文獻範圍**不一致**？
3. 列出至少一個 **「只從資料看不出來、但生成器或文獻有告訴你」** 的規則。

##### A.0 的最終產出：Schema 表

請在 notebook 中產出一張**整合三個來源後**的 schema 表：

| 欄位 | 預期型別 | 合理範圍 | 已知 sentinel | 依據 |
|------|----------|----------|---------------|------|
| `rt_ms` | float | ?–? ms（你決定，並說明理由） | `"NA"` 字串、99999 | 整合 Whelan (2008) + 生成器 + 觀察 |
| `age` | float | ?–?（生成器只用離散值，請自己找出） | `-999` 與 `NaN` | 生成器原始碼第 ? 行 |
| `condition` | category | 應只有 2 個 level；生成器產出 4 個（大小寫不一致） | — | 生成器原始碼第 ? 行 |
| `accuracy` | int | 0 / 1 | — | 生成器原始碼第 ? 行 |
| `subject_id` | int | 整數，幾個 distinct 值？ | — | 生成器原始碼第 ? 行 |

> ⚠️ **重要：來源之間可能會不一致 — 這正是作業的學習重點**
>
> 你會發現課堂 demo（`../../week-12-streamlit_caching_and_data_pipeline/demo/03_pipeline/pipeline.py`）的 `clean()` 用了
> `df["rt_ms"].between(150, 3000)`，而文獻（如 Whelan, 2008）通常採用更嚴格的
> 200–2500 ms。這**不是錯誤** — 它示範了一個真實研究情境：
>
> - 課堂 demo 採寬鬆範圍 → 保留更多 trial、降低 selection bias 風險
> - 文獻採嚴格範圍 → 排除明顯非任務性反應（猜測 / 走神）
>
> **你的工作**：自己做選擇、寫進 schema 表的「依據」欄位、並在 A.4 cleaning
> 時實作這個選擇。**只要理由講得通、引用清楚、結果一致，TA 不會因為你選的
> 範圍跟 demo 不一樣而扣分**。

**評分強調**：每一條規則都要寫出**它從哪個來源來**。沒有依據、純憑直覺寫的範圍**不給分**。

---

#### A.1 Load  · 5 分
- 用 `pd.read_csv()` 讀入 `messy_stroop.csv`
- **不要**做任何 transformation — 純 I/O

#### A.2 Inspect (5 分)
- 印出 `df.shape`、`df.dtypes`、`df.head(5)`
- 用一段文字（2–4 行）描述「我第一眼看到了什麼」

#### A.3 Describe — 健康檢查 (15 分)
跑以下指令並 **逐一解讀**：

```python
df.info()
df.describe(include="all")
df.isnull().sum()
for col in df.select_dtypes("object"):
    print(df[col].value_counts(dropna=False))
```

加上**至少一張視覺化**（建議：histogram 或 boxplot 看 `rt_ms` 分佈，bar chart 看缺值）。

**列出至少四個資料品質問題**，每個問題包含：
- **觀察**：你從哪個指令看出問題？貼出數字 / 截圖
- **可能的原因**：sentinel value？dtype 錯誤？編碼不一致？

#### A.4 Fix — Observation-driven cleaning (20 分)
寫一個 **pure function** `clean(df) -> df`，把 A.3 觀察到的每個問題都修掉。

**強制要求**：

1. 每一個 cleaning 步驟必須在 docstring / 註解中寫明：
   - **觀察**（對應到 A.3 哪一條）
   - **動作**（用了哪個 pandas API）
   - **代價**（這個動作犧牲了什麼）

2. 每一步要 `print` 出 row 數變化（before → after），讓我看得到清理過程的影響：
   ```python
   before = len(df)
   df = df.dropna(subset=["rt_ms"])
   print(f"dropna(rt_ms): {before} → {len(df)}  (lost {before - len(df)} rows)")
   ```

3. `clean()` **不可以**改到輸入的 DataFrame（要 `df = df.copy()`）。

4. **禁止**使用 `df.dropna()` 不帶 `subset=` — 你要知道自己在 drop 什麼。

#### A.5 Re-describe — 驗證 fix (5 分)
- 對 cleaning 後的 df 再跑一次 `describe(include="all")` 與 `value_counts`
- 用 1–2 段文字說：「相比 A.3，現在哪些問題消失了？哪些統計值改變了？」

#### A.6 Analyse — 回答研究問題 (10 分)
- 計算 `congruent` 與 `incongruent` 兩個條件的 **mean RT 與 SD**
- 計算 **Stroop effect** = `mean(incongruent) − mean(congruent)`
- 把這部分寫成**獨立的 `analyse(df, *, outlier_sd=3.0)` function**，並把 `outlier_sd` 暴露成參數
- 用 1 段文字解釋：**為什麼這個 outlier 閾值放在 `analyse()` 而不是 `clean()`？**

> 提示：本週上課強調的「cleaning 與 analysis 邊界」紀律。

---

## Part B — Streamlit Dashboard (`app.py`)  · 30 分

把你 A 部分的成果包裝成一個小的 Streamlit dashboard。**不要求視覺華麗**，要求功能正確。

### 必須包含

#### B.1 `@st.cache_data` 正確使用 (10 分)
- `load_data(path)` 函式必須掛 `@st.cache_data`
- 至少設定一個非預設參數（`ttl=` / `max_entries=` / `show_spinner=`），並在註解說明選擇理由
- `clean()` 也應該被 cache（或被一個 cached 函式呼叫）— 因為對同樣輸入它是 deterministic 的

#### B.2 Sidebar 篩選器 (5 分)
至少兩個 widget，例如：
- `st.multiselect` 篩 `subject_id`
- `st.slider` 篩 `rt_ms` 範圍
- `st.selectbox` 切換要顯示的指標

Widget 值要**經由 boolean mask** 反映在主畫面。

#### B.3 主畫面內容 (15 分)
至少包含**三個** 區塊：

- **KPI metrics**：用 `st.metric` 顯示 `n trials`、`mean RT congruent`、`mean RT incongruent`、`Stroop effect`
- **至少一張圖**：`st.pyplot` 或 `st.bar_chart` — 例如 condition × subject 的 mean RT bar chart
- **資料表**：cleaning 後的 `df.head()` 或 group 摘要

### 加分條件 (最多 +5 分，不超過 Part B 上限)

- 在頁面上顯示 `st.cache_data` 命中與否（用 `time.perf_counter()` 計時）— 對應 demo 中 `app_with_cache.py` 的計時器
- 在 sidebar 加一個 `"Clear cache"` 按鈕

---

## README (`README.md`)  · 10 分

**不超過 1 頁**，包含：

1. **怎麼跑** — 安裝指令、`streamlit run app.py`
2. **資料來源** — 引用 dataset 路徑 + 你查到的 1 篇文獻（APA 格式）
3. **三條最重要的 cleaning 決定** — 一句話一條，每條註明依據來源（生成器 / 文獻 / 觀察）
4. **outlier_sd 為什麼放 analyse() 而不是 clean()** — 一段話

---

## 4. 評分標準 (Rubric)

| 項目 | 分數 |
|------|------|
| **Part A — Pipeline 完整性** (65) | |
| A.0 Data Source & Schema Investigation — 三來源 triangulation 完整、引用文獻、整合 schema 表有依據 | **10** |
| A.1 Load + A.2 Inspect 完整 | 5 |
| A.3 Describe — 至少四個觀察、每個觀察有具體數字佐證 | 15 |
| A.4 Fix — 「觀察→動作→代價」紀律完整，每步 print log，**且每條 cleaning rule 連結回 A.0 schema 表** | 20 |
| A.5 Re-describe — 比對清楚 | 5 |
| A.6 Analyse — Stroop effect 計算正確、outlier 閾值放對位置且解釋清楚 | 10 |
| **Part B — Streamlit Dashboard** (25) | |
| B.1 `@st.cache_data` 正確使用、參數合理 | 10 |
| B.2 Sidebar 至少兩個 widget、boolean mask 正確 | 5 |
| B.3 主畫面 KPI + 圖 + 表三項齊全 | 10 |
| **整體** (10) | |
| README 清楚簡潔 | 10 |
| **合計** | **100** |
| **加分** | **+0–5** |

---

## 5. 評分時 TA 會特別檢查的事

這些是常見會被扣分的地方，請在繳交前自我檢查：

- [ ] A.0 是否引用了 1 篇 Stroop 文獻？是否引用了生成器原始碼的具體行號？
- [ ] A.0 的 schema 表每一條規則都有「依據」欄位嗎？
- [ ] A.4 的每個 cleaning 步驟可以對應回 A.0 schema 表中的哪一條規則嗎？
- [ ] `clean()` 是 pure function 嗎？(`df = df.copy()` 在最前面？)
- [ ] 每個 cleaning 步驟有對應到 A.3 的觀察嗎？
- [ ] 沒有 `df.dropna()` 不帶 `subset=` 的呼叫？
- [ ] outlier threshold 是不是被誤放在 `clean()` 裡？
- [ ] `@st.cache_data` 的 cached function 內**沒有**呼叫 `st.slider` 等 widget？
- [ ] Streamlit app 跑起來沒有 error，sidebar 互動正常更新畫面？

---

## 6. 提示 & 常見錯誤 (Tips & Pitfalls)

### 6.0 A.0 一條好條目長什麼樣

下面這是**兩個都及格**的 A.0 schema 表條目（給你參考**格式與思考方式** —
不要原封不動抄寫，要做出自己的選擇）：

**範例 A — 採用文獻嚴格範圍**
```markdown
| `rt_ms` | float | 200–2500 ms | `"NA"` (字串), `99999` | • Whelan (2008) p. 480 指出 RT < 200ms 多為 anticipation、RT > 2500ms 多為 lapse；採用此範圍可排除非任務性反應。<br>• 生成器第 28 行 `np.random.normal(500, 80, N)` → 中心 500、SD 80，200–2500 涵蓋約 ±25 SD，正常 trial 不會被剔除。<br>• 生成器第 30、35 行注入 `"NA"` 與 `99999` 兩個 sentinel。<br>• 取捨：較嚴格 → 可能多丟 5–10% 真實但極端的 trial，換取較乾淨的 condition mean。 |
```

**範例 B — 採用課堂 demo 較寬鬆範圍**
```markdown
| `rt_ms` | float | 150–3000 ms | `"NA"` (字串), `99999` | • 課堂 demo `pipeline.py` 採用此範圍，理由是保留更多 trial、降低 selection bias 風險。<br>• 生成器第 28 行 `np.random.normal(500, 80, N)` → 寬鬆範圍仍可剔除所有 99999 sentinel。<br>• 文獻（Whelan 2008）會採更嚴格範圍 200–2500 — 我選擇較寬鬆者，因為 dataset 規模僅 200 trial，n 損失敏感。<br>• 取捨：保留 ~3–5% 的可疑慢速 trial，後續分析中需用 mean ± 3 SD trimming 補救（放在 `analyse()`）。 |
```

**兩條都會拿到滿分**。共通的好條目特徵：

- 範圍**不是「教師說的」**，而是**有引用**（哪篇文獻、哪個生成器行號、哪個觀察）
- **明確說明取捨** — 「我選了 X，犧牲的是 Y，得到的是 Z」
- Sentinel 值**