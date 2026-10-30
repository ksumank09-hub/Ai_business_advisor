# AI-Powered Business Entrepreneur Assistant
## Comprehensive Project Dataset & Data Architecture Report

---

### Executive Summary

This report provides a formal, comprehensive audit of all datasets, text corpora, and relational database schemas used in the **AI-Powered Business Entrepreneur Assistant** major project. 

The application integrates machine learning, generative AI, and decision-support systems to assist startup founders:
1. **Supervised Learning (Classification)**: Predicts business risk level using `business_dataset.csv` with a Random Forest model.
2. **Unsupervised Learning (Clustering)**: Segments consumer bases using `customer_dataset.csv` with K-Means clustering.
3. **Information Retrieval (RAG)**: Grounds generative natural-language guidance using a curated 5-document text knowledge base in `knowledge_base/`.
4. **Relational Data Persistence**: Stores user accounts, chat dialogues, financial profiles, and business plans in a SQLite database (`app.db`).

---

## 1. Primary Machine Learning Dataset: `business_dataset.csv`

### 1.1 Overview & Identification
* **File Path**: `ai_business_assistant/data/business_dataset.csv`
* **Format**: Comma-Separated Values (CSV), UTF-8 encoded
* **Sample Count**: **600 records**
* **Attribute Count**: **8 columns** (7 feature variables + 1 target variable)
* **Missing / Null Values**: **0** across all columns (100% data completeness)
* **Intended Task**: Multi-class classification of entrepreneurial risk (`Low Risk`, `Medium Risk`, `High Risk`)

### 1.2 Data Dictionary

| Column Identifier | Semantic Name | Storage Type | Domain / Valid Range | Description |
| :--- | :--- | :--- | :--- | :--- |
| `business_type` | Business Industry | Categorical (`object`) | 8 distinct industry classes | Domain of business operation |
| `investment` | Initial Capital | Numerical (`int64`) | ₹25,000 to ₹20,00,000 | Total startup expenditure required |
| `market_demand` | Market Demand Level | Categorical (`object`) | `Low`, `Medium`, `High` | Estimated market appetite for product/service |
| `competition` | Competitor Density | Categorical (`object`) | `Low`, `Medium`, `High` | Existing market saturation level |
| `experience` | Founder Experience | Categorical (`object`) | `Low`, `Medium`, `High` | Practical entrepreneurial domain experience |
| `operating_cost` | Monthly Overhead | Numerical (`float64`) | ₹1,257.83 to ₹4,96,043.54 | Recurring monthly operational burn rate |
| `target_market` | Target Market Size | Categorical (`object`) | `Small`, `Medium`, `Large` | Addressable customer demographic scale |
| `risk_level` | **Risk Category (Target)**| Categorical (`object`) | `Low Risk`, `Medium Risk`, `High Risk` | Multi-class target variable |

---

### 1.3 Parametric & Statistical Distributions

#### Numerical Features Summary ($N = 600$)

| Statistical Metric | `investment` (INR ₹) | `operating_cost` (INR ₹ / month) |
| :--- | :--- | :--- |
| **Mean ($\mu$)** | ₹5,79,500.00 | ₹90,084.45 |
| **Standard Deviation ($\sigma$)** | ₹6,03,542.80 | ₹1,09,253.29 |
| **Minimum** | ₹25,000.00 | ₹1,257.83 |
| **25th Percentile ($Q_1$)** | ₹1,00,000.00 | ₹12,212.24 |
| **50th Percentile (Median)** | ₹3,00,000.00 | ₹47,130.63 |
| **75th Percentile ($Q_3$)** | ₹10,00,000.00 | ₹1,22,620.00 |
| **Maximum** | ₹20,00,000.00 | ₹4,96,043.54 |
| **Skewness Tendency** | Right-skewed (high-capital outliers) | Right-skewed (moderate-burn concentration) |

---

#### Categorical Features Frequency Breakdown ($N = 600$)

```
[business_type]
├── E-commerce         : 82 (13.67%)
├── Retail             : 77 (12.83%)
├── Technology         : 77 (12.83%)
├── Fashion & Clothing : 77 (12.83%)
├── Food & Beverage    : 76 (12.67%)
├── Services           : 75 (12.50%)
├── Manufacturing      : 68 (11.33%)
└── Education          : 68 (11.33%)

[market_demand]
├── Medium : 239 (39.83%)
├── High   : 207 (34.50%)
└── Low    : 154 (25.67%)

[competition]
├── Medium : 245 (40.83%)
├── High   : 231 (38.50%)
└── Low    : 124 (20.67%)

[experience]
├── Medium : 250 (41.67%)
├── Low    : 197 (32.83%)
└── High   : 153 (25.50%)

[target_market]
├── Small  : 222 (37.00%)
├── Medium : 194 (32.33%)
└── Large  : 184 (30.67%)
```

---

### 1.4 Target Variable Distribution & Imbalance Handling

| Target Class | Absolute Count | Relative Proportion | Class Weighting Strategy |
| :--- | :---: | :---: | :--- |
| **Medium Risk** | 275 | 45.83% | Balanced regular penalty |
| **High Risk** | 251 | 41.83% | Balanced regular penalty |
| **Low Risk** | 74 | 12.33% | Up-weighted via `class_weight="balanced"` in scikit-learn |
| **Total** | **600** | **100.00%** | Multi-class target |

---

### 1.5 Machine Learning Feature Importance Analysis

When evaluated with the trained `RandomForestClassifier` (200 trees, `max_depth=8`, random state 42), the relative Gini importance of features in driving risk decisions is:

1. **`operating_cost` (25.67%)**: Dominant predictor; high ongoing burn without verified revenue strongly indicates venture failure risk.
2. **`investment` (15.13%)**: Capital exposure scaling; higher upfront sunk cost increases downside volatility.
3. **`experience` (14.20%)**: Operational proficiency mitigating execution hazards.
4. **`business_type` (12.21%)**: Structural failure rates inherent to specific industries.
5. **`market_demand` (11.94%)**: Baseline revenue generation potential.
6. **`competition` (11.32%)**: Pricing power and margin compression risks.
7. **`target_market` (9.52%)**: Total addressable audience scale.

---

### 1.6 Experimental Evaluation Metrics

Evaluated on held-out test data (120 test rows):

* **Overall Test Accuracy**: **70.83%**
* **Weighted Precision**: **0.7070**
* **Weighted Recall**: **0.7083**
* **Weighted F1-Score**: **0.7028**

#### Confusion Matrix (Actual vs. Predicted)

| Actual \ Predicted | High Risk | Low Risk | Medium Risk | Class Support |
| :--- | :---: | :---: | :---: | :---: |
| **High Risk** | **38** | 1 | 11 | 50 |
| **Low Risk** | 1 | **6** | 8 | 15 |
| **Medium Risk** | 12 | 2 | **41** | 55 |

---

## 2. Customer Segmentation Dataset: `customer_dataset.csv`

### 2.1 Overview & Identification
* **File Path**: `ai_business_assistant/data/customer_dataset.csv`
* **Format**: Comma-Separated Values (CSV), UTF-8 encoded
* **Sample Count**: **300 customer records**
* **Attribute Count**: **4 numerical columns**
* **Missing / Null Values**: **0** (100% data completeness)
* **Intended Task**: Unsupervised customer segmentation via K-Means Clustering ($K=4$) to inform marketing personas and pricing strategy.

---

### 2.2 Numerical Attributes & Distribution ($N = 300$)

| Feature | Data Type | Min | Mean ($\mu$) | Median | Max | Std Dev ($\sigma$) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `age` | `int64` | 18 | 34.22 yrs | 34 yrs | 59 | 10.49 |
| `income` | `float64` | ₹15,347.86 | ₹69,867.22 | ₹50,123.17 | ₹2,46,907.80 | ₹58,547.63 |
| `purchase_frequency` | `int64` | 1 | 5.21 / mo | 5 / mo | 14 | 3.14 |
| `spending_amount` | `float64` | ₹501.04 | ₹8,138.97 | ₹4,339.38 | ₹38,887.65 | ₹9,693.01 |

---

### 2.3 Cluster Profiling ($K = 4$ Segmentation)

The pipeline standardizes features via `StandardScaler` and clusters customers using `KMeans(n_clusters=4, random_state=42)`. Clusters are sorted by mean spending and labeled into operational cohorts:

| Segment Persona | Cohort Size | Average Age | Average Income | Purchase Frequency | Mean Monthly Spend | Recommended Strategy |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Budget Customers** | 110 (36.7%) | 23.5 yrs | ₹25,790.56 | 2.31 / mo | ₹1,608.64 | Entry-level pricing, discount coupons, mobile-first engagement |
| **Regular Customers**| 97 (32.3%) | 35.8 yrs | ₹52,041.74 | 5.16 / mo | ₹4,713.59 | Value bundles, loyalty reward programs, retention outreach |
| **Premium Customers**| 48 (16.0%) | 44.4 yrs | ₹97,165.21 | 7.17 / mo | ₹11,028.34 | High-tier packages, priority support, quality-focused branding |
| **High-Value Customers**| 45 (15.0%)| 46.1 yrs | ₹1,86,916.12 | 10.29 / mo | ₹28,403.59 | VIP onboarding, bespoke services, executive account management |

---

## 3. RAG Knowledge Base Corpus (`knowledge_base/`)

The Retrieval-Augmented Generation (RAG) system grounds LLM and Demo Mode responses in curated business knowledge chunks.

* **Retriever Engine**: `scikit-learn` `TfidfVectorizer(stop_words="english")` + Cosine Similarity matching
* **Total Documents**: **5 `.txt` files**
* **Total Paragraph Chunks**: **32 discrete index chunks**
* **Corpus Volume**: **~9,400 characters, ~1,292 words**

### Knowledge Base Inventory

```
knowledge_base/
├── business_ideas.txt    (2,045 chars | 277 words | 7 chunks)
│   └── Low-capital ventures, service startups, e-commerce models, cloud kitchens
├── finance.txt           (1,913 chars | 267 words | 6 chunks)
│   └── Working capital, cash runway, break-even calculus, bootstrap vs. venture financing
├── marketing.txt         (1,939 chars | 263 words | 7 chunks)
│   └── Customer Acquisition Cost (CAC), funnel optimization, organic SEO, viral loops
├── risk_management.txt   (1,640 chars | 234 words | 6 chunks)
│   └── Cash buffers, regulatory adherence, supplier dependency mitigation, pivot signals
└── startup_strategy.txt  (1,863 chars | 251 words | 6 chunks)
    └── Lean methodology, MVP iteration, product-market fit, unit economics
```

---

## 4. Operational Relational Schema (`instance/app.db`)

Managed via **Flask-SQLAlchemy** over SQLite:
* `User`: user authentication, password hashing, and credentials.
* `Conversation` & `Message`: chat sessions, intent categories, and retrieved RAG citation snippets.
* `Prediction`: stored risk prediction evaluations and class probability vectors.
* `BusinessProfile` & `BusinessPlan`: saved business profiles, financial metrics, and generated 10-section business plans.

---

## 5. Academic Integrity & Methodological Statement

1. **Synthetic Generation Methodology**:
   All tabular data points (`business_dataset.csv`, `customer_dataset.csv`) were synthetically generated to model realistic micro-economic relationships while avoiding proprietary or non-distributable data dependencies.
2. **Zero-Failure Demo Capability**:
   The self-contained nature of the datasets, pre-trained `.pkl` artifacts, and static `.txt` knowledge base allows the complete application to run offline in **Demo Mode**, satisfying all academic viva examination requirements without third-party API dependencies.
3. **Data Quality Assurance**:
   Zero missing values, rigorous type adherence, stratified train/test validation, and automated test coverage verify reproducible results across host machines.
