"""
Evaluation Harness – tests/eval_harness.py
==========================================
Tests 5+ feedback comments with MOCKED LLM responses so the tests
are deterministic and repeatable (no live API calls needed).

Each test checks:
  - Input comment
  - Expected category
  - Expected urgent flag
  - Actual result from parse_reply → is_valid → apply_safety_net
  - Pass / Fail
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import json

# Make sure we can import from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import (
    parse_reply,
    is_valid,
    apply_safety_net,
    process_comment,
    classify,
)


class TestEvalHarness(unittest.TestCase):
    """
    Five evaluation tests with mocked LLM responses.
    We mock classify() so no real API call is made.
    """

    # ------------------------------------------------------------------
    # Test 1: Taste complaint
    # ------------------------------------------------------------------
    @patch("main.classify")
    def test_taste_complaint(self, mock_classify):
        """Rice was too salty → category=taste, urgent=False"""
        comment = "Rice was too salty today"

        # Simulate what the LLM would return
        mock_classify.return_value = json.dumps({
            "category": "taste",
            "sentiment": "negative",
            "urgent": False,
            "summary": "Rice was too salty"
        })

        result = process_comment(comment)

        self.assertIsNotNone(result, "Result should not be None")
        self.assertEqual(result["category"], "taste")
        self.assertFalse(result["urgent"])
        print("Test 1 PASSED: Taste complaint → category=taste, urgent=False")

    # ------------------------------------------------------------------
    # Test 2: Hygiene complaint (insect)
    # ------------------------------------------------------------------
    @patch("main.classify")
    def test_hygiene_insect(self, mock_classify):
        """Found insect in sambar → category=hygiene, urgent=True"""
        comment = "Found a small insect in the sambar"

        mock_classify.return_value = json.dumps({
            "category": "hygiene",
            "sentiment": "negative",
            "urgent": True,
            "summary": "Insect found in sambar"
        })

        result = process_comment(comment)

        self.assertIsNotNone(result)
        self.assertEqual(result["category"], "hygiene")
        self.assertTrue(result["urgent"])
        print("Test 2 PASSED: Hygiene insect → category=hygiene, urgent=True")

    # ------------------------------------------------------------------
    # Test 3: Quantity complaint
    # ------------------------------------------------------------------
    @patch("main.classify")
    def test_quantity_complaint(self, mock_classify):
        """Less quantity of rice → category=quantity, urgent=False"""
        comment = "Less quantity of rice. I had to leave hungry"

        mock_classify.return_value = json.dumps({
            "category": "quantity",
            "sentiment": "negative",
            "urgent": False,
            "summary": "Insufficient rice served"
        })

        result = process_comment(comment)

        self.assertIsNotNone(result)
        self.assertEqual(result["category"], "quantity")
        self.assertFalse(result["urgent"])
        print("Test 3 PASSED: Quantity complaint → category=quantity, urgent=False")

    # ------------------------------------------------------------------
    # Test 4: Positive feedback
    # ------------------------------------------------------------------
    @patch("main.classify")
    def test_positive_feedback(self, mock_classify):
        """Food was tasty today → category=taste, sentiment=positive, urgent=False"""
        comment = "Food was tasty today. Really enjoyed the idli and chutney"

        mock_classify.return_value = json.dumps({
            "category": "taste",
            "sentiment": "positive",
            "urgent": False,
            "summary": "Enjoyed the idli and chutney"
        })

        result = process_comment(comment)

        self.assertIsNotNone(result)
        self.assertEqual(result["category"], "taste")
        self.assertEqual(result["sentiment"], "positive")
        self.assertFalse(result["urgent"])
        print("Test 4 PASSED: Positive feedback → sentiment=positive, urgent=False")

    # ------------------------------------------------------------------
    # Test 5: Food poisoning / spoiled food
    # ------------------------------------------------------------------
    @patch("main.classify")
    def test_food_poisoning(self, mock_classify):
        """Food poisoning reported → category=hygiene, urgent=True"""
        comment = "Food poisoning case reported. My roommate vomited after lunch"

        mock_classify.return_value = json.dumps({
            "category": "hygiene",
            "sentiment": "negative",
            "urgent": True,
            "summary": "Food poisoning and vomiting after lunch"
        })

        result = process_comment(comment)

        self.assertIsNotNone(result)
        self.assertEqual(result["category"], "hygiene")
        self.assertTrue(result["urgent"])
        print("Test 5 PASSED: Food poisoning → category=hygiene, urgent=True")

    # ------------------------------------------------------------------
    # Test 6 (bonus): Safety net catches missed urgency
    # ------------------------------------------------------------------
    @patch("main.classify")
    def test_safety_net_catches_missed_urgency(self, mock_classify):
        """LLM says urgent=False but comment has 'worm' → safety net fixes it"""
        comment = "I saw a small worm in the vegetable curry"

        # Simulate LLM missing the urgency
        mock_classify.return_value = json.dumps({
            "category": "hygiene",
            "sentiment": "negative",
            "urgent": False,
            "summary": "Worm found in curry"
        })

        result = process_comment(comment)

        self.assertIsNotNone(result)
        self.assertTrue(result["urgent"],
                        "Safety net should have set urgent=True for 'worm'")
        print("Test 6 PASSED: Safety net raised urgency for 'worm'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
