import unittest
from unittest.mock import patch

from backend.tests.evaluation_support import isolated_backend


class PracticalRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = isolated_backend(live=False)
        cls.backend = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    def run_agent(self, question, history=None):
        return self.backend["agent_service"].run_agent({
            "question": question,
            "history": history or [],
        })

    def test_stroke_paraphrases_trigger_danger_before_rag(self):
        response = self.run_agent("我爸刚刚突然说话含糊，右手也抬不起来")

        self.assertEqual(response["action"], "danger_alert")
        self.assertTrue(response["is_danger"])
        self.assertIn("急救电话120", response["answer"])

    def test_lab_report_request_returns_capability_boundary(self):
        response = self.run_agent("C反应蛋白高了一点，是不是细菌感染，需要吃什么药？")

        self.assertEqual(response["action"], "ask_followup")
        self.assertEqual(response["intent"], "capability_boundary")
        self.assertIn("不包括化验单或检验指标解读", response["answer"])
        self.assertIn("不要自行使用抗生素", response["answer"])

    def test_vague_elderly_discomfort_asks_before_rag(self):
        response = self.run_agent("家里老人最近总是不舒服，应该怎么办？")

        self.assertEqual(response["action"], "ask_followup")
        self.assertTrue(response["need_followup"])
        self.assertEqual(response["retrieved_docs"], [])

    def test_followup_detail_after_symptom_description_does_not_repeat_generic_questions(self):
        response = self.run_agent(
            "可能熬夜的有点多，别的也没什么。可能压力有一点",
            history=[
                {
                    "role": "user",
                    "content": "我头有点晕，精神也不好，怎么回事。能给出我一点建议吗？",
                },
                {
                    "role": "assistant",
                    "content": "请先补充以下信息：主要不舒服的部位、持续多久、有没有危险表现。",
                    "action": "ask_followup",
                    "intent": "followup",
                },
            ],
        )

        self.assertNotEqual(response["action"], "ask_followup")
        self.assertFalse(response["need_followup"])

    def test_followup_answer_is_written_to_personal_history_when_persisting(self):
        agent_service = self.backend["agent_service"]
        with patch.object(agent_service, "add_history_record", return_value={"id": 123}) as add_history:
            response = agent_service.run_agent({"question": "我不舒服", "user_id": 49})

        self.assertEqual(response["action"], "ask_followup")
        self.assertEqual(response["history_id"], 123)
        add_history.assert_called_once()

    def test_combined_medicine_question_retrieves_both_drugs(self):
        response = self.run_agent("我一直吃阿司匹林，今天能再吃布洛芬吗？")
        titles = {doc["title"] for doc in response["retrieved_docs"]}

        self.assertEqual(response["action"], "medicine_query")
        self.assertEqual(titles, {"阿司匹林肠溶片", "布洛芬片"})

    def test_read_only_retest_does_not_write_history_or_search_log(self):
        agent_service = self.backend["agent_service"]
        with (
            patch.object(agent_service, "add_history_record") as add_history,
            patch.object(agent_service, "add_search_log") as add_search,
        ):
            response = agent_service.run_agent(
                {"question": "布洛芬有什么禁忌？"},
                persist=False,
            )

        self.assertTrue(response["success"])
        self.assertEqual(response["action"], "medicine_query")
        self.assertIsNone(response["history_id"])
        add_history.assert_not_called()
        add_search.assert_not_called()

    def test_review_retest_uses_session_context_before_target_question(self):
        import main

        record = {
            "id": 99,
            "session_id": 7,
            "question": "这个药能自己停吗？",
            "agent_meta": {},
        }
        session_detail = {
            "messages": [
                {"role": "user", "content": "布洛芬有什么禁忌？"},
                {
                    "role": "assistant",
                    "content": "布洛芬需要注意胃肠道风险。",
                    "history_id": 10,
                    "trace": {"current_topic": "布洛芬片"},
                    "retrieved_docs": [{"title": "布洛芬片", "doc_type": "medicine"}],
                },
                {"role": "user", "content": "先不说布洛芬了，阿司匹林肠溶片有什么副作用？"},
                {
                    "role": "assistant",
                    "content": "阿司匹林可能增加出血风险。",
                    "history_id": 11,
                    "trace": {"current_topic": "阿司匹林肠溶片"},
                    "retrieved_docs": [{"title": "阿司匹林肠溶片", "doc_type": "medicine"}],
                },
                {"role": "user", "content": "这个药能自己停吗？"},
                {
                    "role": "assistant",
                    "content": "原回答",
                    "history_id": 99,
                    "trace": {"current_topic": "阿司匹林肠溶片"},
                },
            ]
        }

        with patch.object(main, "get_session_detail", return_value=session_detail):
            history, context = main.build_review_retest_history(record)

        self.assertEqual(context["source"], "session")
        self.assertEqual(context["used_count"], 4)
        self.assertEqual(history[-1]["current_topic"], "阿司匹林肠溶片")
        self.assertFalse(any(item.get("content") == "这个药能自己停吗？" for item in history))

    def test_switch_phrase_does_not_retrieve_old_drug(self):
        response = self.run_agent(
            "先不说布洛芬了，阿司匹林肠溶片能自己停吗？",
            history=[{"role": "assistant", "current_topic": "布洛芬片"}],
        )
        titles = {doc["title"] for doc in response["retrieved_docs"]}

        self.assertEqual(titles, {"阿司匹林肠溶片"})

    def test_inherited_stop_question_has_direct_offline_answer(self):
        response = self.run_agent(
            "这个药能自己停吗？",
            history=[{
                "role": "assistant",
                "content": "阿司匹林可能增加出血风险。",
                "current_topic": "阿司匹林肠溶片",
                "docs": [{"title": "阿司匹林肠溶片", "doc_type": "medicine"}],
            }],
        )

        self.assertEqual(response["action"], "medicine_query")
        self.assertIn("不建议自行停用阿司匹林肠溶片", response["answer"])
        self.assertIn("医生或药师", response["answer"])

    def test_resolved_history_has_useful_empty_retrieval_fallback(self):
        response = self.run_agent("两个月前胸痛去医院检查过，后来缓解了，现在没有不舒服，日常需要注意什么？")

        self.assertEqual(response["action"], "rag_answer")
        self.assertEqual(response["retrieved_docs"], [])
        self.assertIn("记录是否再次出现", response["answer"])
        self.assertIn("急诊就医", response["answer"])

    def test_text_empty_retrieval_fallback_does_not_ask_for_image_details(self):
        response = self.run_agent("一个没有知识库资料的健康问题")

        self.assertNotIn("如果是图片问题", response["answer"])


if __name__ == "__main__":
    unittest.main()
