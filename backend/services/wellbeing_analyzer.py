import re
from typing import Dict, Any, List, Tuple

# Comprehensive signal dictionaries for keyword-driven analysis fallback/enrichment
DIMENSION_KEYWORDS = {
    "social": {
        "negative": [
            "lonely", "no friends", "left out", "ignored", "bullied", "peer pressure",
            "fake friends", "drama", "awkward", "isolated", "nobody talks to me",
            "hate talking to people", "friend group", "fight with my friend", "social anxiety",
            "alone", "unwanted", "invisible", "bullies", "fight with friend"
        ],
        "positive": [
            "hung out with friends", "best friend", "good conversation", "connected",
            "team", "supportive friends", "fun with friends", "invited me", "made a new friend",
            "friends", "hanging out", "laughing together"
        ]
    },
    "family": {
        "negative": [
            "parents yell", "parents fighting", "disappointed in me", "strict parents",
            "family pressure", "expectations", "compare me to", "grounded", "argument with mom",
            "argument with dad", "family conflict", "nobody understands at home", "sibling fight",
            "parents", "family fight", "yelling at home", "scolded"
        ],
        "positive": [
            "parents were supportive", "family dinner", "mom helped", "dad listened",
            "good talk with parents", "fun with sibling", "peaceful at home", "family support",
            "supportive family"
        ]
    },
    "academic": {
        "negative": [
            "exam", "exams", "studied all night", "studying all night", "cramming", "test",
            "tests", "exam pressure", "failed test", "failing", "so many assignments",
            "too much homework", "can't focus", "behind on studies", "grades dropped",
            "college stress", "fear of failure", "competitive", "syllabus", "procrastinating",
            "tutoring", "mock exam", "homework", "grades", "marks"
        ],
        "positive": [
            "did well on test", "finished assignment", "understood the topic", "good grades",
            "teacher praised", "study session went well", "feeling confident about exams",
            "motivated", "aced the test", "homework done"
        ]
    },
    "digital": {
        "negative": [
            "scrolling till 3am", "doomscrolling", "addicted to phone", "screen time",
            "instagram making me sad", "cyberbullying", "comparing myself online", "tiktok all night",
            "can't put phone down", "late night gaming", "notifications stressing me",
            "screen", "phone all night", "scrolling", "instagram", "tiktok"
        ],
        "positive": [
            "digital detox", "screen break", "put phone away", "productive online",
            "healthy boundaries", "unfollowed toxic accounts", "turned off notifications"
        ]
    },
    "lifestyle": {
        "negative": [
            "couldn't sleep", "insomnia", "sleeping 3 hours", "always tired", "exhausted",
            "skipped breakfast", "junk food", "no energy", "headache", "fatigue",
            "haven't gone outside", "no exercise", "irregular routine", "no sleep",
            "sleep", "tired", "headaches", "drained"
        ],
        "positive": [
            "slept 8 hours", "woke up refreshed", "went for a walk", "ate healthy",
            "exercised", "gym", "played sports", "morning routine", "feeling energetic",
            "good sleep", "healthy food", "walk"
        ]
    }
}

EMOTION_KEYWORDS = {
    "anxious": ["anxious", "nervous", "scared", "panicking", "worried", "freaking out", "uneasy", "stress", "stressed"],
    "exhausted": ["exhausted", "tired", "burned out", "drained", "no energy", "fatigued", "headache"],
    "overwhelmed": ["overwhelmed", "drowning", "too much", "can't handle", "suffocating"],
    "lonely": ["lonely", "alone", "isolated", "invisible", "unwanted", "left out"],
    "frustrated": ["frustrated", "angry", "annoyed", "pissed", "irritated", "mad"],
    "hopeless": ["hopeless", "pointless", "why bother", "give up", "worthless"],
    "hopeful": ["hopeful", "optimistic", "looking forward", "better tomorrow", "trying"],
    "calm": ["calm", "relaxed", "peaceful", "okay", "chill", "content"],
    "happy": ["happy", "excited", "proud", "great day", "relieved", "smiling"]
}

class WellbeingAnalyzer:
    """
    Analyzes user utterances across Social, Family, Academic, Digital, and Lifestyle dimensions.
    Calculates emotional states and smooths dynamic scores.
    """

    @classmethod
    def analyze_message(
        cls,
        text: str,
        current_scores: Dict[str, float],
        llm_analysis: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Calculates emotional cues, dimension signals, and updated 5-dimension scores.
        """
        text_lower = text.lower()

        # 1. Detect emotions
        detected_emotions = []
        for emotion, keywords in EMOTION_KEYWORDS.items():
            if any(re.search(r"\b" + re.escape(kw) + r"\b", text_lower) for kw in keywords):
                detected_emotions.append(emotion)

        if llm_analysis and "emotions" in llm_analysis:
            for em in llm_analysis["emotions"]:
                if em not in detected_emotions:
                    detected_emotions.append(em)

        # 2. Extract dimension signals & calculate point shifts
        dimension_signals: Dict[str, List[str]] = {
            "social": [],
            "family": [],
            "academic": [],
            "digital": [],
            "lifestyle": []
        }
        updated_scores: Dict[str, float] = dict(current_scores)
        score_deltas: Dict[str, float] = {}

        for dim, kw_groups in DIMENSION_KEYWORDS.items():
            neg_matches = [kw for kw in kw_groups["negative"] if re.search(r"\b" + re.escape(kw) + r"\b", text_lower)]
            pos_matches = [kw for kw in kw_groups["positive"] if re.search(r"\b" + re.escape(kw) + r"\b", text_lower)]

            signals = []
            if neg_matches:
                signals.extend([f"negative: {kw}" for kw in neg_matches])
            if pos_matches:
                signals.extend([f"positive: {kw}" for kw in pos_matches])

            dimension_signals[dim] = signals

            # Calculate adjustment
            shift = (len(pos_matches) * 6.0) - (len(neg_matches) * 8.0)

            # Integrate LLM dimension impact if present
            if llm_analysis and "dimension_impacts" in llm_analysis:
                llm_impact = llm_analysis["dimension_impacts"].get(dim, 0.0)
                shift += float(llm_impact)

            # Apply bounded change with momentum
            new_val = max(10.0, min(98.0, current_scores.get(dim, 70.0) + shift))
            updated_scores[dim] = round(new_val, 1)
            score_deltas[dim] = round(new_val - current_scores.get(dim, 70.0), 1)

        # Overall average score (for reference without reducing to a single diagnosis)
        avg_score = round(sum(updated_scores.values()) / len(updated_scores), 1)

        return {
            "emotions": detected_emotions if detected_emotions else ["reflective"],
            "dimension_signals": dimension_signals,
            "updated_scores": updated_scores,
            "score_deltas": score_deltas,
            "wellbeing_summary_index": avg_score
        }
