import unittest
from unittest.mock import patch

from analytics_service import build_quality_diagnosis
from history_service import classify_review_issue


def make_record(**overrides):
    record = {
        "id": 1,
        "question": "我咳嗽两天",
        "answer": "根据知识库资料，建议观察症状并注意危险信号。",
        "warning": {"has_warning": False, "matched": []},
        "retrieved_docs": [
            {
                "title": "咳嗽",
                "doc_type": "disease",
                "score": 0.82,
            }
        ],
        "agent_meta": {
            "action": "rag_answer",
            "intent": "symptom_query",
            "confidence": 0.86,
        },
        "rating": 0,
        "feedback_text": "",
        "is_error": False,
        "review_status": "auto",
    }
    record.update(overrides)
    return record


class ReviewWorkflowTests(unittest.TestCase):
    def test_normal_answer_does_not_create_review_ticket(self):
        issue = classify_review_issue(make_record())

        self.assertFalse(issue["needs_review"])
        self.assertEqual(issue["review_status"], "not_required")

    def test_low_confidence_answer_is_pending_automatically(self):
        issue = classify_review_issue(make_record(
            retrieved_docs=[],
            agent_meta={
                "action": "rag_answer",
                "intent": "symptom_query",
                "confidence": 0.42,
            },
        ))

        self.assertTrue(issue["needs_review"])
        self.assertEqual(issue["review_status"], "pending")

    def test_manual_processed_status_overrides_automatic_review(self):
        issue = classify_review_issue(make_record(
            retrieved_docs=[],
            review_status="processed",
            agent_meta={
                "action": "rag_answer",
                "intent": "symptom_query",
                "confidence": 0.42,
            },
        ))

        self.assertFalse(issue["needs_review"])
        self.assertEqual(issue["review_status"], "processed")


class AnalyticsModeTests(unittest.TestCase):
    def test_historical_snapshot_does_not_claim_improvement(self):
        history = [make_record(
            retrieved_docs=[],
            agent_meta={
                "action": "rag_answer",
                "intent": "symptom_query",
                "confidence": 0.42,
            },
        )]

        result = build_quality_diagnosis(history, deep_recheck=False)

        self.assertEqual(result["analysis_mode"], "historical_snapshot")
        self.assertEqual(result["quality_overview"]["improved_count"], 0)
        self.assertEqual(result["review_suggestions"][0]["status"], "historical_only")

    @patch("analytics_service.current_search")
    def test_current_recheck_can_mark_an_old_issue_improved(self, current_search):
        current_search.return_value = [
            {
                "title": "咳嗽",
                "doc_type": "disease",
                "score": 0.88,
            }
        ]
        history = [make_record(
            retrieved_docs=[],
            agent_meta={
                "action": "rag_answer",
                "intent": "symptom_query",
                "confidence": 0.42,
            },
        )]

        result = build_quality_diagnosis(history, deep_recheck=True)

        self.assertEqual(result["analysis_mode"], "current_recheck")
        self.assertEqual(result["quality_overview"]["improved_count"], 1)
        self.assertEqual(result["improved_cases"][0]["status"], "improved")


if __name__ == "__main__":
    unittest.main()
