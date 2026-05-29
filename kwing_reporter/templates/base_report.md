# KRYSTA WING // WEEKLY MODEL ANALYSIS REPORT

## [SYSTEM METADATA]
* **Target Model:** {{ model_name }}
* **Evaluation Week:** Week {{ week }}
* **Analysis Timestamp:** {{ timestamp }}
* **Modality Profile:** {{ modality | upper }}

---

## [1. COMPUTE & PERFORMANCE BENCHMARKS]
| Metric | Observed Value | Status |
| :--- | :--- | :--- |
| **Inference Latency** | {{ latency }} ms / sample | {% if latency < 50 %}OPTIMAL{% else %}DEGRADED{% endif %} |
| **Peak VRAM Allocation** | {{ vram }} MB | COMPLIANT |
| **Evaluation Loss** | {{ loss }} | RECORDED |

---

## [2. MODALITY INSIGHTS & ARTIFACTS]
{{ modality_specific_content }}

---

## [3. SYSTEM STATUS SUMMARY]
> **Automated Engine Verdict:** Weekly benchmarking run completed for {{ model_name }}. Evaluation artifacts have been successfully compiled and archived into the workspace directory.