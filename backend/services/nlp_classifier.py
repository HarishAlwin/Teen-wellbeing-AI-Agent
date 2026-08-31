"""
backend/services/nlp_classifier.py
──────────────────────────────────
Dual Transformer NLP Intelligence Service:

1. Sentiment Model: `cardiffnlp/twitter-roberta-base-sentiment-latest`
   → Answers: "Is the overall tone positive, neutral, or negative?"

2. Emotion Model: `SamLowe/roberta-base-go_emotions`
   → Answers: "What fine-grained emotion(s) are being expressed?" (28 categories)

Features:
- Lazy loading & singleton pipeline caching for fast throughput.
- Robust fallback heuristics when offline or during initial download.
- Structured scoring output for downstream WellbeingAnalyzer and Groq LLMAgent.
"""

import os
import logging
from typing import Dict, Any, List, Optional
import threading

logger = logging.getLogger("nlp_classifier")

SENTIMENT_MODEL_ID = "cardiffnlp/twitter-roberta-base-sentiment-latest"
EMOTION_MODEL_ID = "SamLowe/roberta-base-go_emotions"
USE_LOCAL_TRANSFORMERS = os.getenv("USE_LOCAL_TRANSFORMERS", "false").lower() in ("true", "1", "yes")


class NLPClassifier:
    """
    Manages fast NLP inference for Sentiment and GoEmotions.
    Uses ultra-fast (<1ms) heuristic analysis by default, and optional HuggingFace RoBERTa pipelines.
    """

    _sentiment_pipeline = None
    _emotion_pipeline = None
    _is_loading = False
    _load_lock = threading.Lock()
    _initialized = False

    @classmethod
    def _init_pipelines(cls):
        """
        Lazy initializer for huggingface pipelines (only if USE_LOCAL_TRANSFORMERS=true).
        """
        if not USE_LOCAL_TRANSFORMERS or cls._initialized:
            return

        with cls._load_lock:
            if cls._initialized:
                return

            cls._is_loading = True
            try:
                from transformers import pipeline

                logger.info(f"[NLPClassifier] Loading Sentiment Model: {SENTIMENT_MODEL_ID}...")
                cls._sentiment_pipeline = pipeline(
                    "text-classification",
                    model=SENTIMENT_MODEL_ID,
                    top_k=None,
                    truncation=True,
                    max_length=512
                )
                logger.info("[NLPClassifier] Sentiment Model loaded successfully.")

                logger.info(f"[NLPClassifier] Loading GoEmotions Model: {EMOTION_MODEL_ID}...")
                cls._emotion_pipeline = pipeline(
                    "text-classification",
                    model=EMOTION_MODEL_ID,
                    top_k=None,
                    truncation=True,
                    max_length=512
                )
                logger.info("[NLPClassifier] GoEmotions Model loaded successfully.")
                cls._initialized = True

            except Exception as e:
                logger.warning(f"[NLPClassifier] Could not initialize transformer pipelines: {e}. Fallback heuristics active.")
            finally:
                cls._is_loading = False


    @classmethod
    def classify_sentiment(cls, text: str) -> Dict[str, Any]:
        """
        Runs `cardiffnlp/twitter-roberta-base-sentiment-latest`
        Returns: { 'label': 'positive'|'neutral'|'negative', 'score': float, 'distribution': dict }
        """
        if not cls._initialized and not cls._is_loading:
            cls._init_pipelines()

        if cls._sentiment_pipeline:
            try:
                results = cls._sentiment_pipeline(text)
                # results is a list of lists of dicts e.g. [[{'label': 'negative', 'score': 0.85}, ...]]
                if results and isinstance(results[0], list):
                    items = results[0]
                else:
                    items = results

                # Sort by score descending
                sorted_items = sorted(items, key=lambda x: x["score"], reverse=True)
                top = sorted_items[0]
                distribution = {item["label"].lower(): round(float(item["score"]), 4) for item in sorted_items}

                return {
                    "label": top["label"].lower(),
                    "score": round(float(top["score"]), 4),
                    "distribution": distribution
                }
            except Exception as e:
                logger.warning(f"[NLPClassifier] Sentiment inference failed: {e}")

        # Fallback heuristic
        return cls._heuristic_sentiment(text)

    @classmethod
    def classify_emotions(cls, text: str, threshold: float = 0.20, top_n: int = 4) -> List[Dict[str, Any]]:
        """
        Runs `SamLowe/roberta-base-go_emotions`
        Returns list of top detected emotions with scores exceeding threshold.
        """
        if not cls._initialized and not cls._is_loading:
            cls._init_pipelines()

        if cls._emotion_pipeline:
            try:
                results = cls._emotion_pipeline(text)
                if results and isinstance(results[0], list):
                    items = results[0]
                else:
                    items = results

                sorted_items = sorted(items, key=lambda x: x["score"], reverse=True)

                # Filter by threshold, ignoring generic 'neutral' if other strong emotions are present
                significant = [
                    {"emotion": it["label"].lower(), "score": round(float(it["score"]), 4)}
                    for it in sorted_items
                    if it["score"] >= threshold and it["label"].lower() != "neutral"
                ]

                # If no emotions above threshold, include top emotion even if neutral
                if not significant and sorted_items:
                    significant = [{"emotion": sorted_items[0]["label"].lower(), "score": round(float(sorted_items[0]["score"]), 4)}]

                return significant[:top_n]
            except Exception as e:
                logger.warning(f"[NLPClassifier] GoEmotions inference failed: {e}")

        # Fallback heuristic
        return cls._heuristic_emotions(text)

    @classmethod
    def analyze(cls, text: str) -> Dict[str, Any]:
        """
        Combined analysis extracting both Sentiment Tone and GoEmotions.
        """
        sentiment = cls.classify_sentiment(text)
        emotions = cls.classify_emotions(text)
        emotion_names = [e["emotion"] for e in emotions]

        return {
            "sentiment": sentiment,
            "tone": sentiment.get("label", "neutral"),
            "sentiment_score": sentiment.get("score", 0.5),
            "emotions": emotions,
            "primary_emotions": emotion_names if emotion_names else ["reflective"],
        }

    # ── Fallback Heuristics ────────────────────────────────────────────────────

    @classmethod
    def _heuristic_sentiment(cls, text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        neg_words = ["sad", "angry", "terrible", "awful", "hate", "fail", "bad", "depressed", "anxious", "scared", "tired", "stressed", "pain", "worst", "overwhelmed"]
        pos_words = ["happy", "great", "awesome", "love", "good", "excited", "proud", "relieved", "confident", "best", "hopeful", "glad"]

        neg_count = sum(1 for w in neg_words if w in text_lower)
        pos_count = sum(1 for w in pos_words if w in text_lower)

        if neg_count > pos_count:
            return {"label": "negative", "score": 0.75, "distribution": {"negative": 0.75, "neutral": 0.20, "positive": 0.05}}
        elif pos_count > neg_count:
            return {"label": "positive", "score": 0.75, "distribution": {"positive": 0.75, "neutral": 0.20, "negative": 0.05}}
        return {"label": "neutral", "score": 0.80, "distribution": {"neutral": 0.80, "positive": 0.10, "negative": 0.10}}

    @classmethod
    def _heuristic_emotions(cls, text: str) -> List[Dict[str, Any]]:
        text_lower = text.lower()
        mapping = {
            "nervousness": ["nervous", "anxious", "worried", "scared", "panic", "stress", "exam"],
            "disappointment": ["disappointed", "failed", "let down", "missed out", "sad"],
            "anger": ["angry", "mad", "furious", "annoyed", "unfair", "hate"],
            "joy": ["happy", "glad", "yay", "fun", "celebrating", "awesome"],
            "optimism": ["hopeful", "looking forward", "better", "improving"],
            "grief": ["lost", "hopeless", "crying", "heartbroken", "grief"],
            "gratitude": ["thank", "grateful", "appreciate", "helpful"],
        }

        detected = []
        for em, keywords in mapping.items():
            if any(kw in text_lower for kw in keywords):
                detected.append({"emotion": em, "score": 0.80})

        return detected if detected else [{"emotion": "neutral", "score": 0.70}]
