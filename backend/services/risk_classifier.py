import re
from typing import Dict, Any, List, Tuple

# Emergency & Helpline Directory by Country
HELPLINES = {
    "IN": {
        "country": "India",
        "emergency": "112",
        "resources": [
            {
                "name": "CHILDLINE (National Child Helpline)",
                "number": "1098",
                "availability": "24/7 Free Call",
                "type": "Children & Youth Support"
            },
            {
                "name": "Tele-MANAS (Govt. of India Mental Health Helpline)",
                "number": "14416 / 1800-891-4416",
                "availability": "24/7 Toll-free, Multilingual",
                "type": "Comprehensive Mental Health"
            },
            {
                "name": "Vandrevala Foundation Helpline",
                "number": "+91 9999 666 555",
                "availability": "24/7 Free Psychological Support & WhatsApp",
                "type": "Crisis & Emotional Support"
            },
            {
                "name": "iCall Psychosocial Helpline (TISS)",
                "number": "+91 9152987821",
                "availability": "Mon-Sat 8:00 AM - 10:00 PM",
                "type": "Youth & Student Counseling"
            },
            {
                "name": "KIRAN Helpline",
                "number": "1800-599-0019",
                "availability": "24/7 Toll-free",
                "type": "Mental Health Rehabilitation"
            }
        ]
    },
    "US": {
        "country": "United States",
        "emergency": "911",
        "resources": [
            {
                "name": "988 Suicide & Crisis Lifeline",
                "number": "988",
                "availability": "24/7 Call & Text",
                "type": "Crisis & Mental Health"
            },
            {
                "name": "Crisis Text Line",
                "number": "Text HOME to 741741",
                "availability": "24/7 Free Text Support",
                "type": "Youth Crisis Support"
            },
            {
                "name": "The Trevor Project (LGBTQ Youth)",
                "number": "1-866-488-7386 or Text START to 678-678",
                "availability": "24/7 Support",
                "type": "Youth Support"
            }
        ]
    },
    "UK": {
        "country": "United Kingdom",
        "emergency": "999",
        "resources": [
            {
                "name": "Childline UK",
                "number": "0800 1111",
                "availability": "24/7 Free Call",
                "type": "Children & Teen Support"
            },
            {
                "name": "Shout Crisis Text Line",
                "number": "Text SHOUT to 85258",
                "availability": "24/7 Free Text",
                "type": "Crisis Support"
            }
        ]
    }
}

# Rule-based safety trigger patterns.
#
# IMPORTANT: These patterns are matched against NORMALIZED text (see
# _normalize_text below), which lowercases input, strips apostrophes, and
# expands common contractions/slang ("wanna" -> "want to", "gonna" -> "going
# to", etc.). Because of that normalization step, write every pattern here
# WITHOUT apostrophes and using the expanded form of contractions — e.g.
# write "dont want to wake up", not "don't want to wake up", and rely on
# normalization to convert "wanna die" into "want to die" before matching.
#
# This list was previously missing common teen phrasing/slang entirely
# (e.g. "wanna die" never matched "want to die"), which meant real crisis
# messages were silently classified as NORMAL. Treat any further additions
# to this list as safety-critical — under-matching here is far worse than
# an occasional false positive.
CRISIS_PATTERNS = [
    r"\b(suicid|kill myself|want to die|wish i was dead|wish i were dead|end my life|end it all|"
    r"better off dead|hang myself|slit my wrist|take all my pills|overdose|unaliv\w*|kms|sewerslide)\b",
    r"\b(cant go on living|no reason to live|no point in living|not worth living|life isnt worth living|"
    r"dont want to wake up|dont want to be here anymore|dont want to exist|"
    r"goodbye forever|ready to end it|hurting myself|cut myself|cutting myself|self harm|self-harm)\b"
]

HIGH_CONCERN_PATTERNS = [
    r"\b(nobody cares|completely hopeless|worthless|cant take this anymore|hate my life|"
    r"trapped with no way out|nobody loves me|everyone hates me|whats the point of anything)\b",
    r"\b(giving away (my )?(stuff|things|possessions|belongings|everything)|feels? pointless keeping (it|them|anything))\b",
    r"\b((nobody|no one) would notice if i (just )?(stopped|disappeared|was gone|was not here|were not here))\b",
    r"\b(panic attack|hyperventilating|cant breathe|shaking uncontrollably|starving myself|"
    r"havent eaten in days|purging)\b",
    r"\b(abused|being hit|someone is hurting me|threatened|assaulted|unsafe at home|stalked)\b"
]

CONCERNING_PATTERNS = [
    r"\b(so overwhelmed|burnout|exhausted|failing everything|ruined my future|crying every day|"
    r"cant sleep at all|no friends|bullied)\b",
    r"\b(parents scream at me|feel so lonely|isolated|terrified of exams|freaking out|"
    r"hopeless about grades|scared to go to school|stopped showing up)\b"
]

class RiskClassifier:
    """
    Multilevel Risk & Safety Assessment Engine.
    Ensures early intervention and immediate protection while remaining supportive.
    """

    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Lowercases, strips apostrophes, and expands common contractions/slang
        so regex patterns don't have to enumerate every surface form of the
        same phrase. This is what makes "i wanna die" match the same pattern
        as "i want to die" — previously it did not, which was a critical
        safety gap.
        """
        t = text.lower()
        t = t.replace("’", "'")
        # Expand common contractions/slang BEFORE stripping apostrophes,
        # since some of these forms don't use one at all ("wanna", "gonna").
        replacements = [
            (r"\bwanna\b", "want to"),
            (r"\bgonna\b", "going to"),
            (r"\bgotta\b", "got to"),
            (r"\bimma\b", "i am going to"),
            (r"\bi'm\b", "i am"),
            (r"\bcan't\b", "cant"),
            (r"\bdon't\b", "dont"),
            (r"\bdoesn't\b", "doesnt"),
            (r"\bwon't\b", "wont"),
            (r"\bisn't\b", "isnt"),
            (r"\bhaven't\b", "havent"),
        ]
        for pattern, repl in replacements:
            t = re.sub(pattern, repl, t)
        # Strip any remaining apostrophes so "can't" (if missed above) and
        # "cant" both normalize the same way as the pattern lists expect.
        t = t.replace("'", "")
        return t

    @classmethod
    def evaluate(
        cls,
        text: str,
        dimension_scores: Dict[str, float] = None,
        score_deltas: Dict[str, float] = None,
        llm_suggested_risk: str = None
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        """
        Returns: (risk_level, trigger_reasons, escalation_guidance)
        Risk levels: NORMAL | CONCERNING | HIGH_CONCERN | IMMEDIATE_SAFETY
        """
        text_lower = cls._normalize_text(text)
        reasons: List[str] = []

        # 1. Check IMMEDIATE_SAFETY triggers (highest priority rule)
        for pattern in CRISIS_PATTERNS:
            if re.search(pattern, text_lower):
                reasons.append("Crisis language or self-harm indicator detected in conversation.")
                return "IMMEDIATE_SAFETY", reasons, cls._get_guidance("IMMEDIATE_SAFETY")

        # 2. Check HIGH_CONCERN text triggers
        for pattern in HIGH_CONCERN_PATTERNS:
            if re.search(pattern, text_lower):
                reasons.append("High distress, extreme hopelessness, or safety concern expressed.")

        # 3. Check CONCERNING text triggers
        for pattern in CONCERNING_PATTERNS:
            if re.search(pattern, text_lower):
                reasons.append("Severe stress, persistent isolation, or intense academic/family struggle noted.")

        # 4. Check dimension scores & sudden deviations from baseline
        if dimension_scores:
            critical_dims = [dim for dim, score in dimension_scores.items() if score <= 30.0]
            low_dims = [dim for dim, score in dimension_scores.items() if 30.0 < score <= 45.0]

            if len(critical_dims) >= 2:
                reasons.append(f"Multiple wellbeing dimensions deeply declined: {', '.join(critical_dims)}.")
            elif len(critical_dims) == 1:
                reasons.append(f"Critical decline in {critical_dims[0]} wellbeing.")

            if len(low_dims) >= 3:
                reasons.append(f"Widespread drop across {', '.join(low_dims)} dimensions.")

        if score_deltas:
            steep_drops = [dim for dim, delta in score_deltas.items() if delta <= -20.0]
            if steep_drops:
                reasons.append(f"Sudden sharp negative shift in {', '.join(steep_drops)}.")

        # 5. Determine level. The LLM's own risk_assessment (see llm_agent.py)
        # is treated as at least as authoritative as the regex reasons above —
        # it can push the level UP (e.g. subtle distress language the fixed
        # keyword patterns miss) but this function is never called in a way
        # that lets it go down, since chat.py always keeps the higher of the
        # two results.
        if llm_suggested_risk == "IMMEDIATE_SAFETY":
            risk_level = "IMMEDIATE_SAFETY"
            reasons.append("LLM reasoning flagged an immediate safety concern.")
        elif any("High distress" in r or "deeply declined" in r for r in reasons) or llm_suggested_risk == "HIGH_CONCERN":
            risk_level = "HIGH_CONCERN"
        elif len(reasons) > 0 or llm_suggested_risk == "CONCERNING":
            risk_level = "CONCERNING"
        else:
            risk_level = "NORMAL"

        return risk_level, reasons, cls._get_guidance(risk_level)

    @classmethod
    def _get_guidance(cls, risk_level: str) -> Dict[str, Any]:
        if risk_level == "IMMEDIATE_SAFETY":
            return {
                "headline": "We want to make sure you are safe right now.",
                "message": "It sounds like you are carrying something really painful and heavy. Please know that you are not alone, and there is immediate, caring support ready for you right now.",
                "action": "Please reach out to a trusted adult, parent, school counselor, or contact the 24/7 free helplines below immediately.",
                "show_helplines": True,
                "urgency": "critical"
            }
        elif risk_level == "HIGH_CONCERN":
            return {
                "headline": "You deserve support for what you're dealing with.",
                "message": "Your recent experiences show you have been dealing with heavy pressure across different areas of life. Talking to someone who understands can make a world of difference before things feel heavier.",
                "action": "We strongly encourage talking with a trusted adult, counselor, or school mentor, or reaching out to a confidential student support helpline.",
                "show_helplines": True,
                "urgency": "high"
            }
        elif risk_level == "CONCERNING":
            return {
                "headline": "Noticing some extra stress lately.",
                "message": "It seems like things have been a bit overwhelming recently. Let's take it one step at a time.",
                "action": "Explore gentle coping strategies and consider opening up to a friend, family member, or teacher you trust.",
                "show_helplines": False,
                "urgency": "medium"
            }
        return {
            "headline": "Things are looking balanced.",
            "message": "Continuing our natural supportive conversations to keep track of your wellbeing goals.",
            "action": "Keep taking care of yourself and maintaining your healthy routines.",
            "show_helplines": False,
            "urgency": "low"
        }

    @classmethod
    def get_helpline_info(cls, country_code: str = "IN") -> Dict[str, Any]:
        return HELPLINES.get(country_code.upper(), HELPLINES["IN"])
