import unittest
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.risk_classifier import RiskClassifier
from services.wellbeing_analyzer import WellbeingAnalyzer
from services.pattern_detector import PatternDetector
from services.llm_agent import LLMAgent

class TestWellbeingIntelligence(unittest.TestCase):

    def test_risk_classifier_immediate_safety(self):
        level, reasons, guidance = RiskClassifier.evaluate("I can't go on living anymore, I want to die")
        self.assertEqual(level, "IMMEDIATE_SAFETY")
        self.assertEqual(guidance["urgency"], "critical")
        self.assertTrue(guidance["show_helplines"])

    def test_risk_classifier_concerning(self):
        level, reasons, guidance = RiskClassifier.evaluate("I'm so overwhelmed with my exams and can't sleep at all")
        self.assertIn(level, ["CONCERNING", "HIGH_CONCERN"])
        self.assertTrue(len(reasons) > 0)

    def test_wellbeing_analyzer_signals(self):
        text = "I studied all night for my exam, had no sleep, and now I have a huge headache and feel exhausted."
        current_scores = {"social": 70.0, "family": 70.0, "academic": 70.0, "digital": 70.0, "lifestyle": 70.0}
        analysis = WellbeingAnalyzer.analyze_message(text, current_scores)

        self.assertTrue("exhausted" in analysis["emotions"] or "anxious" in analysis["emotions"])
        self.assertLess(analysis["updated_scores"]["lifestyle"], 70.0)
        self.assertLess(analysis["updated_scores"]["academic"], 70.0)

    def test_pattern_detector_cross_dimensional(self):
        current_scores = {"social": 50.0, "family": 70.0, "academic": 45.0, "digital": 40.0, "lifestyle": 45.0}
        baseline_scores = {"social": 70.0, "family": 70.0, "academic": 70.0, "digital": 70.0, "lifestyle": 70.0}
        signals = {
            "academic": ["negative: exam pressure"],
            "digital": ["negative: scrolling till 3am"],
            "lifestyle": ["negative: exhausted"],
            "social": ["negative: isolated"],
            "family": []
        }
        emotions = ["exhausted", "anxious"]

        patterns = PatternDetector.detect_patterns(current_scores, baseline_scores, signals, emotions)
        self.assertTrue(len(patterns) > 0)
        pattern_titles = [p["title"] for p in patterns]
        self.assertTrue(any("Academic Pressure" in t or "Baseline Deviation" in t for t in pattern_titles))

    def test_llm_agent_fallback_response(self):
        resp = LLMAgent.generate_response(
            user_message="I'm feeling really stressed about math test tomorrow",
            conversation_history=[],
            current_scores={"academic": 55.0, "social": 70.0, "family": 70.0, "digital": 70.0, "lifestyle": 70.0},
            active_patterns=[],
            risk_level="NORMAL",
            safety_guidance={"message": "All good"}
        )
        self.assertIn("response_text", resp)
        self.assertGreater(len(resp["response_text"]), 10)
        self.assertIn("emotions_detected", resp)

if __name__ == "__main__":
    unittest.main()
