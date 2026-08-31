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

# Rule-based safety trigger patterns
CRISIS_PATTERNS = [
    r"\b(suicid|kill myself|want to die|wanna die|going to die|gonna die|"
    r"i('m| am) dying|end my life|end it all|better off dead|hang myself|"
    r"slit my wrist|take all my pills|overdose)\b",
    r"\b(can't go on living|no reason to live|no point in living|"
    r"don't want to (wake up|be alive|be here)|wish i was dead|wish i were dead|"
    r"goodbye forever|hurting myself|cut myself|self harm|self-harm)\b"
]

HIGH_CONCERN_PATTERNS = [
    r"\b(nobody cares|completely hopeless|worthless|can't take this anymore|hate my life|"
    r"trapped with no way out|nobody loves me|everyone hates me|no one would notice if i (was|were) gone|"
    r"what's the point of anything|i give up|i'm done trying|life isn't worth it|"
    r"nothing matters anymore|i'm a burden|everyone would be better off without me)\b",
    r"\b(panic attack|hyperventilating|can't breathe|shaking uncontrollably|starving myself|"
    r"haven't eaten in days|purging|throwing up on purpose|binge and purge|"
    r"can't stop crying|breaking down|falling apart|losing control of myself)\b",
    r"\b(abused|being hit|someone is hurting me|threatened|assaulted|unsafe at home|stalked|"
    r"scared of my (dad|mom|parent|father|mother|stepdad|stepmom)|locked (in|out) of my room|"
    r"afraid to go home|someone touched me|forced (me|to))\b"
]

CONCERNING_PATTERNS = [
    r"\b(so overwhelmed|burnout|exhausted|failing everything|ruined my future|crying every day|"
    r"can't sleep at all|no friends|bullied|falling behind in everything|can't focus on anything|"
    r"everything feels pointless|nothing i do is good enough|constantly anxious|"
    r"dread going to school|dread waking up)\b",
    r"\b(parents scream at me|feel so lonely|isolated|terrified of exams|freaking out|"
    r"hopeless about grades|scared to go to school|parents fighting all the time|"
    r"no one understands me|left out of everything|excluded from|"
    r"pushed away my friends|stopped talking to everyone)\b"
]

class RiskClassifier:
    """
    Multilevel Risk & Safety Assessment Engine.
    Ensures early intervention and immediate protection while remaining supportive.
    """

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
        text_lower = text.lower()
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

        # 5. Determine level
        if any("High distress" in r or "deeply declined" in r for r in reasons) or llm_suggested_risk == "HIGH_CONCERN":
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
