from typing import Dict, Any, List, Optional
from datetime import datetime

class PatternDetector:
    """
    Identifies cross-dimensional linkages, behavioral deviations from baseline,
    and temporal trends in a teenager's life.

    Task 3: detect_patterns() now also accepts llm_pattern_observations — a list of
    patterns proposed by the LLM (from llm_agent.py). These are merged into the returned
    list alongside rule-based patterns, each tagged with a "source" field:
      - "source": "rule_based"  — from the deterministic rules below (always run)
      - "source": "llm"         — proposed by Gemini based on conversation analysis
    This makes it clear to downstream consumers which patterns were detected how.
    """

    @classmethod
    def detect_patterns(
        cls,
        current_scores: Dict[str, float],
        baseline_scores: Dict[str, float],
        signals: Dict[str, List[str]],
        emotions: List[str],
        recent_history_scores: List[Dict[str, float]] = None,
        # Task 3: LLM-proposed patterns from llm_agent.py
        llm_pattern_observations: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Returns detected patterns with dimensions involved, severity, title, and descriptive explanation.
        Each pattern has a "source" field: "rule_based" or "llm".
        """
        patterns = []

        # 1. Cross-Dimensional Chain Pattern: Academic Pressure -> Late Screen -> Sleep Deficit -> Fatigue
        academic_stress = current_scores.get("academic", 70) < 55 or any("negative" in s for s in signals.get("academic", []))
        digital_strain = current_scores.get("digital", 70) < 55 or any("negative" in s for s in signals.get("digital", []))
        lifestyle_deficit = current_scores.get("lifestyle", 70) < 55 or any("negative" in s for s in signals.get("lifestyle", []))
        social_withdrawal = current_scores.get("social", 70) < 55 or any("negative" in s for s in signals.get("social", []))

        if academic_stress and digital_strain and lifestyle_deficit:
            patterns.append({
                "title": "Academic Pressure & Late-Night Screen Sleep Cycle",
                "description": "High academic demands correlate with late-night phone browsing, resulting in disrupted sleep and compounding fatigue.",
                "category": "cross_dimensional",
                "severity": "high" if "exhausted" in emotions or "overwhelmed" in emotions else "medium",
                "dimensions_involved": ["academic", "digital", "lifestyle"],
                "evidence_snippets": ["Study workload causing stress", "Compulsive late-night screen time", "Fatigue and sleep reduction"],
                "source": "rule_based",
            })

        if lifestyle_deficit and social_withdrawal:
            patterns.append({
                "title": "Fatigue-Induced Social Withdrawal",
                "description": "Physical tiredness and low energy levels appear linked to pulling away from social connections and peer interactions.",
                "category": "cross_dimensional",
                "severity": "medium",
                "dimensions_involved": ["lifestyle", "social"],
                "evidence_snippets": ["Low energy routines", "Decreased social interaction and feelings of isolation"],
                "source": "rule_based",
            })

        # GoEmotions-Driven Pattern: Chronic Nervousness & Perfectionism Strain
        if "nervousness" in emotions or "fear" in emotions:
            if academic_stress or current_scores.get("academic", 70) < 60:
                patterns.append({
                    "title": "Exam Anticipation & Nervous Overload",
                    "description": "Fine-grained emotional signals detect persistent nervousness and performance worry tied to upcoming academic milestones.",
                    "category": "cross_dimensional",
                    "severity": "high" if "fear" in emotions else "medium",
                    "dimensions_involved": ["academic", "lifestyle"],
                    "evidence_snippets": ["GoEmotions flagged acute nervousness", "Academic pressure detected"],
                    "source": "roberta_nlp",
                })

        # GoEmotions-Driven Pattern: Disappointment & Self-Isolation Loop
        if "disappointment" in emotions or "grief" in emotions or "sadness" in emotions:
            if social_withdrawal or current_scores.get("social", 70) < 60:
                patterns.append({
                    "title": "Disappointment & Interpersonal Disconnection",
                    "description": "Feelings of disappointment or sadness correlate with withdrawing from peer groups and social support networks.",
                    "category": "cross_dimensional",
                    "severity": "medium",
                    "dimensions_involved": ["social", "family"],
                    "evidence_snippets": ["GoEmotions identified sadness/disappointment", "Social interaction scores lower than baseline"],
                    "source": "roberta_nlp",
                })

        # 2. Family Pressure & Academic Anxiety Link
        family_conflict = current_scores.get("family", 70) < 55 or any("negative" in s for s in signals.get("family", []))
        if family_conflict and academic_stress:
            patterns.append({
                "title": "Family Expectation & Academic Anxiety Amplification",
                "description": "Pressure regarding grades or expectations at home is intensifying stress surrounding school performance.",
                "category": "cross_dimensional",
                "severity": "medium",
                "dimensions_involved": ["family", "academic"],
                "evidence_snippets": ["Heightened parental expectations", "Anxiety over test scores"],
                "source": "rule_based",
            })

        # 3. Sudden Deviation from Baseline
        for dim, score in current_scores.items():
            base = baseline_scores.get(dim, 70.0)
            if base - score >= 20.0:
                patterns.append({
                    "title": f"Significant Baseline Deviation in {dim.capitalize()}",
                    "description": f"Recent {dim} balance ({score:.0f}) has dropped noticeably below personal baseline ({base:.0f}).",
                    "category": "deviation",
                    "severity": "medium",
                    "dimensions_involved": [dim],
                    "evidence_snippets": [f"{dim.capitalize()} score dropped {base - score:.1f} pts below normal baseline"],
                    "source": "rule_based",
                })

        # 4. Multi-session Trend Evaluation (if history available)
        if recent_history_scores and len(recent_history_scores) >= 3:
            # Check for consecutive declines in any dimension
            for dim in ["social", "family", "academic", "digital", "lifestyle"]:
                vals = [entry.get(dim, 70.0) for entry in recent_history_scores[-3:]]
                if vals[0] > vals[1] > vals[2] and (vals[0] - vals[2]) >= 12.0:
                    patterns.append({
                        "title": f"Declining Trend in {dim.capitalize()}",
                        "description": f"{dim.capitalize()} wellbeing has shown a downward pattern across consecutive sessions.",
                        "category": "trend",
                        "severity": "high" if vals[2] < 45 else "medium",
                        "dimensions_involved": [dim],
                        "evidence_snippets": [f"Steady drop from {vals[0]:.0f} to {vals[2]:.0f} across recent checkpoints"],
                        "source": "rule_based",
                    })
                elif vals[0] < vals[1] < vals[2] and (vals[2] - vals[0]) >= 10.0:
                    patterns.append({
                        "title": f"Positive Recovery Trend in {dim.capitalize()}",
                        "description": f"{dim.capitalize()} habits have steadily improved over the past sessions.",
                        "category": "trend",
                        "severity": "low",
                        "dimensions_involved": [dim],
                        "evidence_snippets": [f"Improvement from {vals[0]:.0f} to {vals[2]:.0f}"],
                        "source": "rule_based",
                    })

        # ── Task 3: Merge LLM-proposed pattern observations ────────────────────
        # LLM patterns are additive to the rule-based set. We deduplicate by title
        # (case-insensitive) so LLM does not re-surface what rules already caught.
        if llm_pattern_observations:
            existing_titles = {p["title"].lower() for p in patterns}
            for llm_pat in llm_pattern_observations:
                title = llm_pat.get("title", "").strip()
                if not title or title.lower() in existing_titles:
                    continue  # Skip duplicates or empty entries
                patterns.append({
                    "title": title,
                    "description": llm_pat.get("description", ""),
                    "category": llm_pat.get("category", "cross_dimensional"),
                    "severity": llm_pat.get("severity", "medium"),
                    "dimensions_involved": llm_pat.get("dimensions_involved", []),
                    "evidence_snippets": llm_pat.get("evidence_snippets", []),
                    "source": "llm",  # Clearly marks this as LLM-observed, not rule-derived
                })
                existing_titles.add(title.lower())

        return patterns
