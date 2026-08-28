from typing import Dict, Any, List
from datetime import datetime

class PatternDetector:
    """
    Identifies cross-dimensional linkages, behavioral deviations from baseline,
    and temporal trends in a teenager's life.
    """

    @classmethod
    def detect_patterns(
        cls,
        current_scores: Dict[str, float],
        baseline_scores: Dict[str, float],
        signals: Dict[str, List[str]],
        emotions: List[str],
        recent_history_scores: List[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Returns detected patterns with dimensions involved, severity, title, and descriptive explanation.
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
                "evidence_snippets": ["Study workload causing stress", "Compulsive late-night screen time", "Fatigue and sleep reduction"]
            })

        if lifestyle_deficit and social_withdrawal:
            patterns.append({
                "title": "Fatigue-Induced Social Withdrawal",
                "description": "Physical tiredness and low energy levels appear linked to pulling away from social connections and peer interactions.",
                "category": "cross_dimensional",
                "severity": "medium",
                "dimensions_involved": ["lifestyle", "social"],
                "evidence_snippets": ["Low energy routines", "Decreased social interaction and feelings of isolation"]
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
                "evidence_snippets": ["Heightened parental expectations", "Anxiety over test scores"]
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
                    "evidence_snippets": [f"{dim.capitalize()} score dropped {base - score:.1f} pts below normal baseline"]
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
                        "evidence_snippets": [f"Steady drop from {vals[0]:.0f} to {vals[2]:.0f} across recent checkpoints"]
                    })
                elif vals[0] < vals[1] < vals[2] and (vals[2] - vals[0]) >= 10.0:
                    patterns.append({
                        "title": f"Positive Recovery Trend in {dim.capitalize()}",
                        "description": f"{dim.capitalize()} habits have steadily improved over the past sessions.",
                        "category": "trend",
                        "severity": "low",
                        "dimensions_involved": [dim],
                        "evidence_snippets": [f"Improvement from {vals[0]:.0f} to {vals[2]:.0f}"]
                    })

        return patterns
