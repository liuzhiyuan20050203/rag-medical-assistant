import base64
import json
import os
import sys
import time
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch


TEST_DIR = Path(__file__).resolve().parent
BACKEND_DIR = TEST_DIR.parent
CASE_DIR = TEST_DIR / "cases"
ASSET_DIR = TEST_DIR / "assets"
FIXTURE_FILE = TEST_DIR / "fixtures" / "knowledge_snapshot.json"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_fixture():
    return load_json(FIXTURE_FILE)


def load_cases():
    cases = []
    for path in sorted(CASE_DIR.glob("*_cases.json")):
        cases.extend(load_json(path))
    return cases


def normalize_name(value):
    text = "".join(str(value or "").lower().split())
    for suffix in ["肠溶片", "胶囊", "颗粒", "口服液", "片"]:
        text = text.removesuffix(suffix)
    return text


def equivalent_title(left, right):
    return normalize_name(left) == normalize_name(right)


def snapshot_medicine_search(medicines, keyword):
    query = normalize_name(keyword)
    if not query:
        return []

    results = []
    for item in medicines:
        name = normalize_name(item.get("name"))
        searchable = normalize_name(
            " ".join([
                item.get("name", ""),
                item.get("type", ""),
                item.get("usage", ""),
            ])
        )
        if name in query or query in name or (len(query) >= 2 and query in searchable):
            results.append(dict(item))
    return results


def disabled_llm(*_args, **_kwargs):
    return {
        "success": False,
        "provider": "offline-evaluation",
        "model": "none",
        "answer": "",
        "plan": None,
        "error": "离线标准测试已禁用外部模型。",
    }


@contextmanager
def isolated_backend(fixture=None, live=False, actual_knowledge=False):
    import agent_service
    import rag_service
    import safety_check

    if actual_knowledge:
        fixture = {
            "diseases": rag_service.get_all_diseases(),
            "medicines": rag_service.get_all_medicines(),
            "warning_rules": safety_check.load_warning_rules(),
        }
    else:
        fixture = fixture or load_fixture()

    diseases = fixture["diseases"]
    medicines = fixture["medicines"]
    warning_rules = fixture["warning_rules"]

    previous_mode = os.environ.get("RAG_EMBEDDING_MODE")
    os.environ["RAG_EMBEDDING_MODE"] = "keyword"

    with ExitStack() as stack:
        stack.enter_context(patch.object(rag_service, "get_all_diseases", return_value=diseases))
        stack.enter_context(patch.object(rag_service, "get_all_medicines", return_value=medicines))
        stack.enter_context(patch.object(agent_service, "get_all_medicines", return_value=medicines))
        stack.enter_context(patch.object(
            agent_service,
            "search_medicine",
            side_effect=lambda keyword: snapshot_medicine_search(medicines, keyword),
        ))
        stack.enter_context(patch.object(safety_check, "load_warning_rules", return_value=warning_rules))
        stack.enter_context(patch.object(agent_service, "add_history_record", return_value={"id": None}))
        stack.enter_context(patch.object(agent_service, "add_search_log", return_value=None))
        if not live:
            stack.enter_context(patch.object(agent_service, "generate_agent_plan", side_effect=disabled_llm))
            stack.enter_context(patch.object(agent_service, "generate_agent_answer", side_effect=disabled_llm))
            stack.enter_context(patch.object(agent_service, "env_flag", return_value=True))

        rag_service.index = None
        rag_service.documents = []
        rag_service.init_vector_store()
        try:
            yield {
                "agent_service": agent_service,
                "rag_service": rag_service,
                "fixture": fixture,
            }
        finally:
            rag_service.index = None
            rag_service.documents = []
            if previous_mode is None:
                os.environ.pop("RAG_EMBEDDING_MODE", None)
            else:
                os.environ["RAG_EMBEDDING_MODE"] = previous_mode


def data_url_for_asset(asset_name):
    path = ASSET_DIR / asset_name
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def combined_observation(result):
    return " ".join(result.get("observations", []) + result.get("capture_tips", []))


def evaluate_expectations(case, response=None, visual=None, live=False):
    expected = case.get("expected", {})
    checks = []

    def add(name, passed, actual=None, wanted=None):
        checks.append({
            "name": name,
            "passed": bool(passed),
            "actual": actual,
            "expected": wanted,
        })

    if visual is not None:
        tags = visual.get("tags", [])
        wanted_tags = expected.get("visual_tags_any", [])
        if wanted_tags:
            add("visual_tags_any", any(item in tags for item in wanted_tags), tags, wanted_tags)

        unwanted_tags = expected.get("visual_tags_none", [])
        if unwanted_tags:
            add("visual_tags_none", not any(item in tags for item in unwanted_tags), tags, unwanted_tags)

        stats = visual.get("visual", {})
        for key, wanted in expected.get("quality_levels", {}).items():
            add(f"quality:{key}", stats.get(key) == wanted, stats.get(key), wanted)

        wanted_observations = expected.get("observations_contains_any", [])
        if wanted_observations:
            text = combined_observation(visual)
            add(
                "observations_contains_any",
                any(item in text for item in wanted_observations),
                text,
                wanted_observations,
            )

        if live:
            vision_result = visual.get("llm") or {}
            add(
                "vision_llm_success",
                bool(vision_result.get("success")),
                vision_result.get("error") or vision_result.get("success"),
                True,
            )

    if response is not None:
        action = response.get("action")
        actions = expected.get("actions_any", [])
        if actions:
            add("actions_any", action in actions, action, actions)

        if "danger" in expected:
            add("danger", bool(response.get("is_danger")) == expected["danger"], bool(response.get("is_danger")), expected["danger"])

        if "need_followup" in expected:
            add("need_followup", bool(response.get("need_followup")) == expected["need_followup"], bool(response.get("need_followup")), expected["need_followup"])

        titles = [doc.get("title", "") for doc in response.get("retrieved_docs", [])]
        wanted_titles = expected.get("retrieved_titles_any", [])
        if wanted_titles:
            add(
                "retrieved_titles_any",
                any(equivalent_title(title, wanted) for title in titles for wanted in wanted_titles),
                titles,
                wanted_titles,
            )

        unwanted_titles = expected.get("retrieved_titles_none", [])
        if unwanted_titles:
            add(
                "retrieved_titles_none",
                not any(equivalent_title(title, unwanted) for title in titles for unwanted in unwanted_titles),
                titles,
                unwanted_titles,
            )

        answer = response.get("answer", "")
        wanted_phrases = expected.get("answer_contains_any", [])
        if wanted_phrases:
            add("answer_contains_any", any(item in answer for item in wanted_phrases), answer[:300], wanted_phrases)

        forbidden = expected.get("answer_forbidden", [])
        if forbidden:
            add("answer_forbidden", not any(item in answer for item in forbidden), answer[:300], forbidden)

    return checks


def evaluate_case(case, backend, live=False):
    import multimodal_service

    started = time.perf_counter()
    visual = None
    response = None
    expected = case.get("expected", {})

    if case.get("asset"):
        with patch.object(multimodal_service, "search_database_context", return_value={"diseases": [], "medicines": [], "has_matches": False}), patch.object(multimodal_service, "search_knowledge", return_value=[]):
            visual = multimodal_service.analyze_image_payload(
                data_url_for_asset(case["asset"]),
                file_name=case["asset"],
                note=case.get("note", ""),
                include_llm=live,
            )
        if expected.get("agent_input"):
            agent_input = dict(expected["agent_input"])
            if live:
                vision_analysis = (visual.get("llm") or {}).get("analysis") or {}
                visible_findings = vision_analysis.get("visible_findings") or []
                if vision_analysis:
                    agent_input["image_summary"] = "；".join(
                        item for item in [
                            vision_analysis.get("summary", ""),
                            vision_analysis.get("likely_scene", ""),
                            "、".join(visible_findings),
                        ] if item
                    )
                    agent_input["image_tags"] = visual.get("tags", [])
            response = backend["agent_service"].run_agent(agent_input)
    else:
        response = backend["agent_service"].run_agent(case.get("input", {}))

    checks = evaluate_expectations(case, response=response, visual=visual, live=live)
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    return {
        "id": case["id"],
        "name": case.get("name", ""),
        "category": case.get("category", ""),
        "severity": case.get("severity", "important"),
        "passed": all(item["passed"] for item in checks),
        "duration_ms": duration_ms,
        "action": (response or {}).get("action", ""),
        "retrieved_titles": [doc.get("title", "") for doc in (response or {}).get("retrieved_docs", [])],
        "llm": (response or {}).get("llm"),
        "vision_llm": (visual or {}).get("llm"),
        "checks": checks,
    }
