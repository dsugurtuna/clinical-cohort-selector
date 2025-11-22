# Clinical Cohort Selector

**A precision medicine toolkit for stratifying patient cohorts based on genotype, age, and gender.**

This repository demonstrates the ability to translate complex clinical study protocols into automated, reproducible code. It focuses on **Participant Recall**: selecting the exact right patients for a study while balancing demographic factors and exclusion criteria.

## 📂 Repository Contents

| Script | Role | Description |
| :--- | :--- | :--- |
| `build_stratified_cohort.sh` | **Cohort Builder** | The core logic. Stratifies female participants into 4 biological age stages (Pre/Peri/Early/Late Menopausal) and builds a statistically age-matched male control group. |
| `impact_analysis_exclusion.sh` | **Feasibility Study** | A diagnostic tool that calculates how many participants would be lost if a new exclusion criterion (e.g., *APOE-e2* carriers) were introduced. Essential for study planning. |
| `integrate_phenotypes.py` | **Data Integration** | A Python utility that merges disparate data sources—genotype data (CSV) and clinical phenotype data (Space-delimited text)—into a single master record. |

## 🌟 Key Capabilities

### 1. Complex Stratification Logic
Clinical trials often require strict demographic balancing. This toolkit automates:
*   **Biological Staging:** Grouping participants not just by age, but by biological relevance (e.g., *Peri-menopausal: 45-49*).
*   **Proportional Matching:** The male control group is not random; it is built to mirror the age distribution of the female cohort exactly.

### 2. Exclusion Criteria Management
*   **Safety First:** The pipeline rigorously filters out participants with specific risk alleles (e.g., *APOE-e2*), ensuring patient safety and study validity.
*   **Impact Assessment:** Before running a recall, the `impact_analysis_exclusion.sh` script predicts the "cost" of these exclusions in terms of participant numbers.

### 3. Reproducible Science
*   **Deterministic Output:** The sorting and selection logic ensures that running the script twice yields the exact same list of patients, which is critical for regulatory compliance.
*   **Audit Trails:** Generates detailed summary reports (`recall_summary.txt`) documenting exactly how many patients were selected for each group.

## 🛠️ Technical Stack

*   **Bash/AWK**: For high-speed text processing and logic implementation.
*   **Python**: For structured data integration and joining.
*   **CSV**: Standardized input/output formats for interoperability with clinical systems.

---
*Created by [dsugurtuna](https://github.com/dsugurtuna)*
