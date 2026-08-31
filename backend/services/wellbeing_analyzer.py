"""
backend/services/wellbeing_analyzer.py
──────────────────────────────────────
Analyzes teenager messages using:
1. `cardiffnlp/twitter-roberta-base-sentiment-latest` -> Overall Tone (positive/neutral/negative)
2. `SamLowe/roberta-base-go_emotions` -> Fine-grained Emotional Expression (28 categories)
3. 5-Dimension Life Impact Scoring (Social, Family, Academic, Digital, Lifestyle)

P2 Keyword Tiers:
  "negative"  — high-signal distress words that score negatively unconditionally
  "positive"  — high-signal positive words that score positively unconditionally
  "context"   — neutral/ambiguous single-token words (e.g. "exam", "parents", "screen")
               that only contribute negative score when EITHER:
               (a) at least one "negative" keyword also matched this dimension, OR
               (b) the overall sentiment tone is "negative"
               This prevents false-positives like "I aced my exam!" scoring academic down.
"""

import re
from typing import Dict, Any, List, Tuple
from services.nlp_classifier import NLPClassifier

DIMENSION_KEYWORDS = {
    "social": {
        "negative": [
            "lonely", "no friends", "left out", "ignored", "bullied", "peer pressure",
            "fake friends", "drama", "awkward", "isolated", "nobody talks to me",
            "hate talking to people", "friend group", "fight with my friend", "social anxiety",
            "alone", "unwanted", "invisible", "bullies", "fight with friend"
        ],
        # "friends", "people" are neutral — kept positive-only or omitted
        "positive": [
            "hung out with friends", "best friend", "good conversation", "connected",
            "team", "supportive friends", "fun with friends", "invited me", "made a new friend",
            "friends", "hanging out", "laughing together"
        ],
        "context": []  # No neutral-ambiguous social tokens needed
    },
    "family": {
        "negative": [
            "parents yell", "parents fighting", "disappointed in me", "strict parents",
            "family pressure", "expectations", "compare me to", "grounded", "argument with mom",
            "argument with dad", "family conflict", "nobody understands at home", "sibling fight",
            "family fight", "yelling at home", "scolded"
        ],
        "positive": [
            "parents were supportive", "family dinner", "mom helped", "dad listened",
            "good talk with parents", "fun with sibling", "peaceful at home", "family support",
            "supportive family"
        ],
        # "parents" alone is neutral — moved to context tier
        "context": ["parents", "family"]
    },
    "academic": {
        "negative": [
            "studied all night", "studying all night", "cramming",
            "exam pressure", "failed test", "failing", "so many assignments",
            "too much homework", "can't focus", "behind on studies", "grades dropped",
            "college stress", "fear of failure", "competitive", "procrastinating",
            "mock exam"
        ],
        "positive": [
            "did well on test", "finished assignment", "understood the topic", "good grades",
            "teacher praised", "study session went well", "feeling confident about exams",
            "motivated", "aced the test", "homework done"
        ],
        # Neutral academic tokens — only penalize when paired with distress signals
        "context": [
            "exam", "exams", "test", "tests", "homework", "grades", "marks",
            "tutoring", "syllabus", "assignment"
        ]
    },
    "digital": {
        "negative": [
            "scrolling till 3am", "doomscrolling", "addicted to phone",
            "instagram making me sad", "cyberbullying", "comparing myself online", "tiktok all night",
            "can't put phone down", "late night gaming", "notifications stressing me",
            "phone all night"
        ],
        "positive": [
            "digital detox", "screen break", "put phone away", "productive online",
            "healthy boundaries", "unfollowed toxic accounts", "turned off notifications"
        ],
        # "screen", "scrolling", "instagram", "tiktok" alone don't imply harm
        "context": ["screen time", "screen", "scrolling", "instagram", "tiktok", "phone"]
    },
    "lifestyle": {
        "negative": [
            "couldn't sleep", "insomnia", "sleeping 3 hours", "always tired", "exhausted",
            "skipped breakfast", "junk food", "no energy", "headache", "fatigue",
            "haven't gone outside", "no exercise", "irregular routine", "no sleep"
        ],
        "positive": [
            "slept 8 hours", "woke up refreshed", "went for a walk", "ate healthy",
            "exercised", "gym", "played sports", "morning routine", "feeling energetic",
            "good sleep", "healthy food", "walk"
        ],
        # "sleep", "tired", "headaches", "drained" alone are neutral — context-tier
        "context": ["sleep", "tired", "headaches", "drained", "rest"]
    }
}


class WellbeingAnalyzer:
    """
    Analyzes user utterances across Social, Family, Academic, Digital, and Lifestyle dimensions.
    Integrates RoBERTa Sentiment & GoEmotions into dimension momentum and longitudinal tracking.

    Keyword scoring uses a two-tier system:
      - "negative"/"positive" keywords score unconditionally
      - "context" keywords only score negative when a negative anchor is also present
        (negative keyword match OR overall sentiment == "negative")
    """

    @classmethod
    def analyze_message(
        cls,
        text: str,
        current_scores: Dict[str, float],
        llm_analysis: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Runs dual RoBERTa analysis (Sentiment + GoEmotions) & computes dimension score adjustments.
        """
        text_lower = text.lower()

        # ── 1. RoBERTa Dual Transformer Analysis ─────────────────────────────
        nlp_result = NLPClassifier.analyze(text)
        sentiment_data = nlp_result["sentiment"]
        tone = nlp_result["tone"]                   # 'positive' | 'neutral' | 'negative'
        emotions_list = nlp_result["emotions"]      # [{'emotion': 'nervousness', 'score': 0.84}, ...]
        primary_emotions = nlp_result["primary_emotions"]

        # ── 2. Dimension Signal Extraction ────────────────────────────────────
        dimension_signals: Dict[str, List[str]] = {
            "social": [],
            "family": [],
            "academic": [],
            "digital": [],
            "lifestyle": []
        }
        updated_scores: Dict[str, float] = dict(current_scores)
        score_deltas: Dict[str, float] = {}

        # Base sentiment shift multiplier
        tone_bias = -3.0 if tone == "negative" else (+2.5 if tone == "positive" else 0.0)

        for dim, kw_groups in DIMENSION_KEYWORDS.items():
            neg_matches = [kw for kw in kw_groups["negative"] if re.search(r"\b" + re.escape(kw) + r"\b", text_lower)]
            pos_matches = [kw for kw in kw_groups["positive"] if re.search(r"\b" + re.escape(kw) + r"\b", text_lower)]
            ctx_matches = [kw for kw in kw_groups.get("context", []) if re.search(r"\b" + re.escape(kw) + r"\b", text_lower)]

            signals = []
            if neg_matches:
                signals.extend([f"negative: {kw}" for kw in neg_matches])
            if pos_matches:
                signals.extend([f"positive: {kw}" for kw in pos_matches])
            if ctx_matches:
                signals.extend([f"context: {kw}" for kw in ctx_matches])

            dimension_signals[dim] = signals

            # Base keyword adjustment — unconditional tiers
            shift = (len(pos_matches) * 5.0) - (len(neg_matches) * 7.0)

            # Context-tier keywords: only penalize if a negative anchor exists
            # Anchor = at least one "negative" keyword OR overall tone is negative
            has_negative_anchor = bool(neg_matches) or tone == "negative"
            if ctx_matches and has_negative_anchor:
                # Lower weight than hard-negative keywords — context contributes 3.5 per match
                shift -= len(ctx_matches) * 3.5

            # Apply RoBERTa tone bias if dimension was actively mentioned
            if neg_matches or pos_matches or (ctx_matches and has_negative_anchor):
                shift += tone_bias

            # Specific emotional modifiers from GoEmotions
            if "nervousness" in primary_emotions and dim in ("academic", "social"):
                shift -= 3.0
            if "grief" in primary_emotions or "sadness" in primary_emotions:
                shift -= 4.0
            if "joy" in primary_emotions or "optimism" in primary_emotions or "relief" in primary_emotions:
                shift += 3.0

            # Integrate LLM dimension impact if present
            if llm_analysis and "dimension_impacts" in llm_analysis:
                llm_impact = llm_analysis["dimension_impacts"].get(dim, 0.0)
                shift += float(llm_impact)

            # Apply bounded change
            new_val = max(10.0, min(98.0, current_scores.get(dim, 70.0) + shift))
            updated_scores[dim] = round(new_val, 1)
            score_deltas[dim] = round(new_val - current_scores.get(dim, 70.0), 1)

        avg_score = round(sum(updated_scores.values()) / len(updated_scores), 1)

        return {
            "sentiment": sentiment_data,
            "tone": tone,
            "emotions": primary_emotions,
            "detailed_emotions": emotions_list,
            "dimension_signals": dimension_signals,
            "updated_scores": updated_scores,
            "score_deltas": score_deltas,
            "wellbeing_summary_index": avg_score
        }





