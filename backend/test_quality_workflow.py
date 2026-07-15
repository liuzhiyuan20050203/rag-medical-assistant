import unittest
from unittest.mock import patch

from analytics_service import (
    build_action_distribution,
    build_demand_counters,
    build_quality_diagnosis,
    build_rag_quality,
    build_word_cloud,
)
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

    def test_review_ticket_keeps_latest_retest_summary(self):
        retest = {
            "retested_at": "2026-07-15 09:30:00",
            "current": {"confidence": 0.82, "top_score": 0.9},
        }
        issue = classify_review_issue(make_record(
            retrieved_docs=[],
            review_retest=retest,
            agent_meta={
                "action": "rag_answer",
                "intent": "symptom_query",
                "confidence": 0.42,
            },
        ))

        self.assertEqual(issue["review_retest"], retest)

    def test_normal_followup_without_docs_does_not_create_ticket(self):
        issue = classify_review_issue(make_record(
            question="请问不舒服的是哪个部位，持续多久了？",
            retrieved_docs=[],
            agent_meta={
                "action": "ask_followup",
                "intent": "need_more_information",
                "confidence": 0.35,
            },
        ))

        self.assertFalse(issue["needs_review"])
        self.assertEqual(issue["review_status"], "not_required")

    def test_bad_feedback_still_creates_ticket_for_followup(self):
        issue = classify_review_issue(make_record(
            retrieved_docs=[],
            rating=1,
            agent_meta={
                "action": "ask_followup",
                "intent": "need_more_information",
                "confidence": 0.35,
            },
        ))

        self.assertTrue(issue["needs_review"])
        self.assertEqual(issue["issue_type"], "用户差评")


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
        improved = result["improved_cases"][0]
        self.assertEqual(improved["status"], "improved")
        self.assertTrue(improved["recheck_applied"])
        self.assertEqual(improved["previous_top_score"], 0)
        self.assertEqual(improved["current_top_score"], 0.88)
        self.assertEqual(improved["score_change"], 0.88)
        self.assertEqual(improved["added_titles"], ["咳嗽"])

    @patch("analytics_service.current_search")
    def test_image_issue_cannot_be_resolved_by_rag_score(self, current_search):
        history = [make_record(
            question="这是什么。图片识别描述：画面较清晰。图片识别标签：general_image",
            retrieved_docs=[{
                "title": "皮肤过敏",
                "doc_type": "disease",
                "score": 0.12,
            }],
            agent_meta={
                "action": "image_assist",
                "intent": "image_question",
                "confidence": 0.45,
            },
        )]

        result = build_quality_diagnosis(history, deep_recheck=True)

        current_search.assert_not_called()
        self.assertEqual(result["quality_overview"]["rechecked_count"], 0)
        self.assertEqual(result["quality_overview"]["improved_count"], 0)
        self.assertEqual(result["review_suggestions"][0]["status"], "needs_review")
        self.assertFalse(result["review_suggestions"][0]["recheck_applied"])

    def test_rag_quality_only_uses_rag_answers(self):
        history = [
            make_record(id=1),
            make_record(
                id=2,
                retrieved_docs=[],
                agent_meta={"action": "medicine_query", "confidence": 0.4},
            ),
            make_record(
                id=3,
                retrieved_docs=[],
                agent_meta={"action": "ask_followup", "confidence": 0.35},
            ),
        ]

        result = build_rag_quality(history)

        self.assertEqual(result["total_cases"], 1)
        self.assertEqual(result["no_retrieval_count"], 0)

    def test_no_retrieval_metric_only_applies_to_rag_answers(self):
        history = [
            make_record(
                id=1,
                retrieved_docs=[],
                agent_meta={"action": "rag_answer", "confidence": 0.4},
            ),
            make_record(
                id=2,
                retrieved_docs=[],
                agent_meta={"action": "ask_followup", "confidence": 0.35},
            ),
        ]

        result = {item["action"]: item for item in build_action_distribution(history)}

        self.assertEqual(result["rag_answer"]["no_retrieval_count"], 1)
        self.assertEqual(result["ask_followup"]["no_retrieval_count"], 0)
        self.assertEqual(result["ask_followup"]["low_confidence_count"], 0)

    def test_word_cloud_excludes_system_generated_image_text(self):
        history = [{
            "question": "我咳嗽两天。图片识别描述：皮肤红疹，画面较清晰。图片识别标签：红疹",
        }]

        result = build_word_cloud(
            history,
            symptoms=["咳嗽", "皮肤红疹"],
            medicines=[],
            warning_rules=[],
        )

        self.assertEqual(result, [{"text": "咳嗽", "value": 1}])


class DemandStatisticsTests(unittest.TestCase):
    def test_symptoms_are_deduplicated_by_session_and_context(self):
        diseases = [{"symptoms": ["咳嗽", "胸痛"]}, {"symptoms": ["咳嗽"]}]
        history = [
            make_record(id=1, session_id=10, question="我咳嗽两天了"),
            make_record(id=2, session_id=10, question="咳嗽晚上更明显"),
            make_record(id=3, session_id=11, question="我没有胸痛，只是咳嗽"),
            make_record(id=4, session_id=12, question="如果胸痛应该怎么办"),
            make_record(id=5, session_id=13, question="我父亲胸痛"),
        ]

        symptom_counter, _disease_counter, _medicine_counter = build_demand_counters(history, diseases)

        self.assertEqual(symptom_counter["咳嗽"], 2)
        self.assertEqual(symptom_counter["胸痛"], 0)

    def test_medicine_consultations_do_not_mix_rag_or_search_logs(self):
        medicine_doc = {"title": "布洛芬片", "doc_type": "medicine"}
        history = [
            make_record(
                id=1,
                session_id=20,
                question="布洛芬有什么注意事项",
                retrieved_docs=[medicine_doc],
                agent_meta={"action": "medicine_query", "current_topic": "布洛芬"},
            ),
            make_record(
                id=2,
                session_id=20,
                question="这个药有什么副作用",
                retrieved_docs=[medicine_doc],
                agent_meta={"action": "medicine_query", "current_topic": "布洛芬片"},
            ),
            make_record(
                id=3,
                session_id=21,
                question="我胃痛",
                retrieved_docs=[medicine_doc],
                agent_meta={"action": "rag_answer", "current_topic": ""},
            ),
        ]

        _symptom_counter, _disease_counter, medicine_counter = build_demand_counters(history, [])

        self.assertEqual(medicine_counter["布洛芬片"], 1)

    def test_disease_retrieval_is_deduplicated_per_answer(self):
        duplicate = {"title": "普通感冒", "doc_type": "disease"}
        history = [make_record(retrieved_docs=[duplicate, duplicate])]

        _symptom_counter, disease_counter, _medicine_counter = build_demand_counters(history, [])

        self.assertEqual(disease_counter["普通感冒"], 1)


if __name__ == "__main__":
    unittest.main()
