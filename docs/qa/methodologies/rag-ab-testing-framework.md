# RAG A/B Testing Framework

**Document Type**: Testing Methodology  
**Date**: 2025-10-22  
**Status**: Approved  
**Related**: Story 7.1 Task 6

---

## Overview

Framework per validazione enhancement RAG (prompt, retrieval, models) tramite A/B testing rigoroso con significatività statistica.

**Scope**: Confrontare varianti RAG system su metriche quantitative e qualitative.

---

## Methodology

### Experiment Design

#### 1. Hypothesis Definition

**Template**:
```
H0 (Null): Il sistema enhanced non differisce dal baseline su metrica X
H1 (Alternative): Il sistema enhanced migliora metrica X di almeno Δ rispetto al baseline

- Metric X: [user_satisfaction | precision@5 | follow_up_rate | ...]
- Δ (Minimum Detectable Effect): [+10% | +0.05 absolute | ...]
- Significance level (α): 0.05 (5% false positive rate)
- Statistical power (1-β): 0.80 (80% chance detect real effect)
```

**Example**:
```
H0: Enhanced academic prompt non migliora user satisfaction vs baseline
H1: Enhanced prompt aumenta user satisfaction di almeno +10pp (es. 62% → 72%)

- Metric: % feedback positivo (thumbs up / total feedback)
- MDE: +10 percentage points
- α: 0.05
- Power: 0.80
```

#### 2. Sample Size Calculation

**Formula** (two-proportion z-test):
```
n = (Z_α/2 + Z_β)² × [p1(1-p1) + p2(1-p2)] / (p2 - p1)²

Where:
- Z_α/2 = 1.96 (for α=0.05, two-tailed)
- Z_β = 0.84 (for power=0.80)
- p1 = baseline rate (es. 0.62)
- p2 = target rate (es. 0.72)
```

**Calculator** (Python):
```python
import scipy.stats as stats
import numpy as np

def calculate_sample_size(
    baseline_rate: float,
    target_rate: float,
    alpha: float = 0.05,
    power: float = 0.80
) -> int:
    """
    Calcola sample size per two-proportion test.
    
    Returns:
        n per gruppo (control + treatment = 2n totale)
    """
    Z_alpha = stats.norm.ppf(1 - alpha/2)
    Z_beta = stats.norm.ppf(power)
    
    p1 = baseline_rate
    p2 = target_rate
    delta = p2 - p1
    
    pooled_p = (p1 + p2) / 2
    pooled_variance = 2 * pooled_p * (1 - pooled_p)
    
    n = (Z_alpha + Z_beta)**2 * pooled_variance / delta**2
    
    return int(np.ceil(n))

# Example
n_per_group = calculate_sample_size(
    baseline_rate=0.62,
    target_rate=0.72,
    alpha=0.05,
    power=0.80
)
print(f"Sample size needed: {n_per_group} per group ({n_per_group*2} total)")
# Output: ~195 per gruppo, 390 totale
```

#### 3. Randomization Strategy

**User-level randomization** (not session-level):
```python
import hashlib

def assign_variant(user_id: str, experiment_id: str) -> str:
    """
    Deterministic user assignment to variant.
    
    Args:
        user_id: User identifier (JWT sub)
        experiment_id: Unique experiment identifier
        
    Returns:
        "control" | "treatment"
    """
    # Hash user_id + experiment_id for deterministic assignment
    hash_input = f"{user_id}:{experiment_id}"
    hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
    
    # 50/50 split
    return "treatment" if hash_value % 2 == 0 else "control"
```

**Rationale**: User-level garantisce consistenza esperienza (stesso utente vede sempre stessa variante).

#### 4. Duration

**Formula**:
```
Duration (days) = Sample size / (Daily active users × Session per user)

Example:
- Sample size: 400 sessions totali (200 per gruppo)
- DAU: 50 studenti
- Sessions per user: 2/day
- Duration = 400 / (50 × 2) = 4 giorni

Raccomandazione: Aggiungere 20% buffer → 5 giorni
```

---

## Metrics

### Primary Metrics

#### 1. User Satisfaction (Qualitative)

**Definition**: % feedback positivo (thumbs up / total feedback)

**Collection**:
```typescript
// Frontend: Feedback widget post-risposta
<FeedbackButtons onFeedback={(vote) => {
  sendFeedback(messageId, vote); // "positive" | "negative"
}} />
```

**Calculation**:
```python
def calculate_satisfaction_rate(feedback_records):
    positive = sum(1 for f in feedback_records if f.vote == "positive")
    total = len(feedback_records)
    return positive / total if total > 0 else 0

# Per variant
control_rate = calculate_satisfaction_rate(control_feedback)
treatment_rate = calculate_satisfaction_rate(treatment_feedback)
```

#### 2. Precision@5 (Quantitative)

**Definition**: % chunk rilevanti nei top-5 retrieved

**Ground Truth**:
- Manual annotation: 50 query representative
- 3 annotatori indipendenti (docenti fisioterapia)
- Kappa agreement ≥ 0.70

**Calculation**:
```python
def precision_at_k(retrieved_ids, relevant_ids, k=5):
    top_k = retrieved_ids[:k]
    hits = len(set(top_k) & set(relevant_ids))
    return hits / k

# Aggregate over test queries
precisions = [
    precision_at_k(result["chunk_ids"], ground_truth[query]["relevant_ids"])
    for query, result in test_results.items()
]
avg_precision = np.mean(precisions)
```

#### 3. Engagement Metrics

**Definitions**:
- **Messages per session**: Avg numero messaggi conversazione
- **Session duration**: Tempo medio sessione (minuti)
- **Follow-up rate**: % sessioni con 2+ messaggi

**Collection**: Analytics events
```python
logger.info({
    "event": "session_ended",
    "session_id": session_id,
    "variant": variant,
    "message_count": message_count,
    "duration_seconds": duration,
})
```

---

### Secondary Metrics

- **Latency p95**: Tempo risposta p95 (ms)
- **Citation accuracy**: % citazioni verificabili
- **Error rate**: % risposte con fallback/errori
- **Concept clarity**: User perception "concetti chiari" (survey)

---

## Statistical Testing

### Two-Proportion Test (Satisfaction)

**Python implementation**:
```python
from scipy.stats import chi2_contingency
import numpy as np

def test_proportion_difference(
    control_positive: int,
    control_total: int,
    treatment_positive: int,
    treatment_total: int,
    alpha: float = 0.05
) -> dict:
    """
    Test significatività differenza tra due proporzioni.
    
    Returns:
        {
            "control_rate": float,
            "treatment_rate": float,
            "difference": float,
            "p_value": float,
            "significant": bool,
            "confidence_interval": (lower, upper)
        }
    """
    # Rates
    p_control = control_positive / control_total
    p_treatment = treatment_positive / treatment_total
    difference = p_treatment - p_control
    
    # Chi-square test
    contingency_table = [
        [control_positive, control_total - control_positive],
        [treatment_positive, treatment_total - treatment_positive]
    ]
    chi2, p_value, dof, expected = chi2_contingency(contingency_table)
    
    # Confidence interval (Wilson score)
    z = 1.96  # 95% CI
    se = np.sqrt(
        p_control * (1 - p_control) / control_total +
        p_treatment * (1 - p_treatment) / treatment_total
    )
    ci_lower = difference - z * se
    ci_upper = difference + z * se
    
    return {
        "control_rate": p_control,
        "treatment_rate": p_treatment,
        "difference": difference,
        "p_value": p_value,
        "significant": p_value < alpha,
        "confidence_interval": (ci_lower, ci_upper)
    }

# Example usage
result = test_proportion_difference(
    control_positive=124,
    control_total=200,
    treatment_positive=156,
    treatment_total=200,
    alpha=0.05
)
print(f"Control: {result['control_rate']:.1%}")
print(f"Treatment: {result['treatment_rate']:.1%}")
print(f"Difference: +{result['difference']:.1%}")
print(f"p-value: {result['p_value']:.4f}")
print(f"Significant: {result['significant']}")
```

### T-Test (Continuous Metrics)

**Example: Session duration**
```python
from scipy.stats import ttest_ind

def test_mean_difference(control_values, treatment_values, alpha=0.05):
    """Welch's t-test (unequal variances)."""
    t_stat, p_value = ttest_ind(treatment_values, control_values, equal_var=False)
    
    control_mean = np.mean(control_values)
    treatment_mean = np.mean(treatment_values)
    difference = treatment_mean - control_mean
    
    # Confidence interval
    se = np.sqrt(
        np.var(control_values, ddof=1) / len(control_values) +
        np.var(treatment_values, ddof=1) / len(treatment_values)
    )
    z = 1.96
    ci_lower = difference - z * se
    ci_upper = difference + z * se
    
    return {
        "control_mean": control_mean,
        "treatment_mean": treatment_mean,
        "difference": difference,
        "p_value": p_value,
        "significant": p_value < alpha,
        "confidence_interval": (ci_lower, ci_upper)
    }
```

---

## Implementation

### Backend Infrastructure

#### 1. Variant Assignment

```python
# apps/api/api/services/ab_testing.py

from typing import Literal
from ..config import Settings

EXPERIMENTS = {
    "enhanced_academic_prompt_v1": {
        "status": "active",
        "start_date": "2025-10-22",
        "end_date": "2025-10-29",
        "traffic_split": 0.50,  # 50% treatment
    }
}

def get_user_variant(
    user_id: str,
    experiment_id: str,
    settings: Settings
) -> Literal["control", "treatment"]:
    """Assign user to variant."""
    
    experiment = EXPERIMENTS.get(experiment_id)
    if not experiment or experiment["status"] != "active":
        return "control"  # Fallback
    
    # Deterministic assignment
    import hashlib
    hash_value = int(hashlib.md5(f"{user_id}:{experiment_id}".encode()).hexdigest(), 16)
    is_treatment = (hash_value % 100) < (experiment["traffic_split"] * 100)
    
    return "treatment" if is_treatment else "control"
```

#### 2. Variant Execution

```python
# apps/api/api/routers/chat.py

@router.post("/sessions/{sessionId}/messages")
def create_chat_message(...):
    # Get user variant
    user_id = payload.get("sub")
    variant = get_user_variant(user_id, "enhanced_academic_prompt_v1", settings)
    
    # Select prompt based on variant
    if variant == "treatment":
        prompt = ENHANCED_ACADEMIC_PROMPT
    else:
        prompt = BASELINE_PROMPT
    
    # Log variant assignment
    logger.info({
        "event": "ab_test_assignment",
        "user_id": user_id,
        "session_id": sessionId,
        "experiment_id": "enhanced_academic_prompt_v1",
        "variant": variant
    })
    
    # Generate response with assigned prompt
    response = chain.invoke({"question": user_message, "prompt": prompt, ...})
    
    # Track metrics with variant tag
    track_metric("response_generated", {
        "variant": variant,
        "latency_ms": duration,
        ...
    })
    
    return response
```

#### 3. Metrics Collection

```python
# apps/api/api/analytics/ab_test_metrics.py

from dataclasses import dataclass
from typing import List

@dataclass
class ABTestMetrics:
    experiment_id: str
    variant: str
    feedback_positive: int
    feedback_negative: int
    session_count: int
    avg_messages_per_session: float
    avg_duration_seconds: float
    follow_up_rate: float

def collect_metrics(experiment_id: str, variant: str) -> ABTestMetrics:
    """Aggregate metrics for variant."""
    # Query analytics store
    sessions = get_sessions_for_variant(experiment_id, variant)
    feedback = get_feedback_for_variant(experiment_id, variant)
    
    return ABTestMetrics(
        experiment_id=experiment_id,
        variant=variant,
        feedback_positive=sum(1 for f in feedback if f.vote == "positive"),
        feedback_negative=sum(1 for f in feedback if f.vote == "negative"),
        session_count=len(sessions),
        avg_messages_per_session=np.mean([s.message_count for s in sessions]),
        avg_duration_seconds=np.mean([s.duration for s in sessions]),
        follow_up_rate=sum(1 for s in sessions if s.message_count >= 2) / len(sessions)
    )
```

---

## Analysis Workflow

### Daily Monitoring

```python
# scripts/monitor_ab_test.py

def daily_ab_test_report(experiment_id: str):
    """Generate daily progress report."""
    
    control_metrics = collect_metrics(experiment_id, "control")
    treatment_metrics = collect_metrics(experiment_id, "treatment")
    
    print("=== A/B Test Daily Report ===")
    print(f"Experiment: {experiment_id}")
    print(f"Date: {datetime.now().date()}")
    print()
    print(f"Control sessions: {control_metrics.session_count}")
    print(f"Treatment sessions: {treatment_metrics.session_count}")
    print()
    
    # Satisfaction rate
    control_rate = control_metrics.feedback_positive / (
        control_metrics.feedback_positive + control_metrics.feedback_negative
    )
    treatment_rate = treatment_metrics.feedback_positive / (
        treatment_metrics.feedback_positive + treatment_metrics.feedback_negative
    )
    
    print(f"Satisfaction Control: {control_rate:.1%}")
    print(f"Satisfaction Treatment: {treatment_rate:.1%}")
    print(f"Difference: {(treatment_rate - control_rate):.1%}")
    print()
    
    # Check if enough data for significance test
    min_samples = 50  # Minimum per gruppo
    if (control_metrics.session_count >= min_samples and 
        treatment_metrics.session_count >= min_samples):
        
        result = test_proportion_difference(
            control_metrics.feedback_positive,
            control_metrics.feedback_positive + control_metrics.feedback_negative,
            treatment_metrics.feedback_positive,
            treatment_metrics.feedback_positive + treatment_metrics.feedback_negative
        )
        
        print(f"Statistical Test:")
        print(f"  p-value: {result['p_value']:.4f}")
        print(f"  Significant: {result['significant']}")
        print(f"  95% CI: [{result['confidence_interval'][0]:.1%}, {result['confidence_interval'][1]:.1%}]")
    else:
        print("Not enough data for statistical test yet.")
```

### Final Analysis (End of Experiment)

```python
def final_ab_test_analysis(experiment_id: str):
    """Comprehensive analysis at experiment end."""
    
    control = collect_metrics(experiment_id, "control")
    treatment = collect_metrics(experiment_id, "treatment")
    
    report = {
        "experiment_id": experiment_id,
        "duration_days": (end_date - start_date).days,
        "total_sessions": control.session_count + treatment.session_count,
        
        # Primary metric: Satisfaction
        "satisfaction_control": ...,
        "satisfaction_treatment": ...,
        "satisfaction_test": test_proportion_difference(...),
        
        # Secondary metrics
        "messages_per_session_control": control.avg_messages_per_session,
        "messages_per_session_treatment": treatment.avg_messages_per_session,
        "messages_test": test_mean_difference(...),
        
        # Decision
        "decision": "LAUNCH" if all_tests_significant else "NO_LAUNCH",
        "reasoning": "..."
    }
    
    # Save report
    save_json(f"reports/ab_test_{experiment_id}_final.json", report)
    
    return report
```

---

## Decision Framework

### Launch Criteria

✅ **Launch treatment** if:
1. Primary metric (satisfaction) significantly improved (p < 0.05)
2. Improvement meets MDE (≥ +10pp)
3. No significant degradation on guardrail metrics (latency p95 < 3s, error rate < 2%)
4. Sample size target reached

❌ **Don't launch** if:
- Not significant OR
- Significant but below MDE OR
- Degradation on guardrails

⚠️ **Iterate** if:
- Mixed results (some metrics up, some down)
- Close to significance (0.05 < p < 0.10)

---

## Example: Enhanced Prompt A/B Test

### Setup

```python
experiment_config = {
    "id": "enhanced_academic_prompt_v1",
    "hypothesis": "Academic medical prompt increases user satisfaction by +10pp",
    "variants": {
        "control": {
            "prompt": BASELINE_PROMPT,
            "description": "Generic assistant prompt"
        },
        "treatment": {
            "prompt": ENHANCED_ACADEMIC_PROMPT,
            "description": "Medical academic tutor prompt"
        }
    },
    "primary_metric": "user_satisfaction_rate",
    "sample_size_per_group": 200,
    "duration_days": 7,
    "start_date": "2025-10-22",
}
```

### Results (Hypothetical)

```
=== Final A/B Test Results ===

Experiment: enhanced_academic_prompt_v1
Duration: 7 days (2025-10-22 to 2025-10-29)
Total sessions: 425

PRIMARY METRIC: User Satisfaction
  Control:   124/200 = 62.0%
  Treatment: 156/205 = 76.1%
  Difference: +14.1pp
  p-value: 0.003 **
  95% CI: [+5.2%, +23.0%]
  
SECONDARY METRICS:
  Messages per session:
    Control: 1.8 ± 0.9
    Treatment: 2.6 ± 1.2
    Difference: +0.8
    p-value: 0.012 *
  
  Session duration (minutes):
    Control: 3.2 ± 1.8
    Treatment: 4.7 ± 2.3
    Difference: +1.5 min
    p-value: 0.008 **
  
  Follow-up rate:
    Control: 32%
    Treatment: 51%
    Difference: +19pp
    p-value: 0.001 ***

GUARDRAIL METRICS:
  Latency p95: 2.1s (✓ < 3s threshold)
  Error rate: 0.8% (✓ < 2% threshold)

DECISION: ✅ LAUNCH TREATMENT
Reasoning: Primary metric significantly improved (+14.1pp, exceeds +10pp MDE).
All secondary metrics improved. No guardrail degradation.
```

---

## References

- Kohavi et al. (2020): "Trustworthy Online Controlled Experiments"
- Google A/B Testing Guide: https://developers.google.com/analytics/devguides/collection/analyticsjs/experiments
- Sample Size Calculator: https://www.evanmiller.org/ab-testing/sample-size.html

---

**Document Owner**: Data Analyst / ML Engineer  
**Review Cycle**: Per experiment  
**Last Updated**: 2025-10-22
