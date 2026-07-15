import argparse
import json
import os
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from backend.tests.evaluation_support import evaluate_case, isolated_backend, load_cases


REPORT_DIR = Path(__file__).resolve().parent / "reports"


def percent(part, total):
    return round(part / total * 100, 1) if total else 0.0


def build_summary(results):
    total = len(results)
    passed = sum(1 for item in results if item["passed"])
    by_category = defaultdict(list)
    severity_failures = Counter()

    for item in results:
        by_category[item["category"]].append(item)
        if not item["passed"]:
            severity_failures[item["severity"]] += 1

    category_summary = {}
    for category, items in sorted(by_category.items()):
        count = len(items)
        category_passed = sum(1 for item in items if item["passed"])
        category_summary[category] = {
            "total": count,
            "passed": category_passed,
            "pass_rate": percent(category_passed, count),
        }

    durations = [item["duration_ms"] for item in results]
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": percent(passed, total),
        "critical_failures": severity_failures["critical"],
        "important_failures": severity_failures["important"],
        "average_duration_ms": round(statistics.mean(durations), 2) if durations else 0,
        "p95_duration_ms": round(sorted(durations)[max(0, int(len(durations) * 0.95) - 1)], 2) if durations else 0,
        "categories": category_summary,
    }


def markdown_report(report):
    summary = report["summary"]
    lines = [
        "# 医疗助手标准评估报告",
        "",
        f"- 生成时间：{report['generated_at']}",
        f"- 评估模式：{report['mode']}",
        f"- 总用例：{summary['total']}",
        f"- 通过：{summary['passed']}",
        f"- 失败：{summary['failed']}",
        f"- 总通过率：{summary['pass_rate']}%",
        f"- 严重失败：{summary['critical_failures']}",
        f"- 平均离线耗时：{summary['average_duration_ms']} ms",
        "",
        "## 分类结果",
        "",
        "| 分类 | 通过 | 总数 | 通过率 |",
        "| --- | ---: | ---: | ---: |",
    ]

    for category, item in summary["categories"].items():
        lines.append(f"| {category} | {item['passed']} | {item['total']} | {item['pass_rate']}% |")

    failures = [item for item in report["results"] if not item["passed"]]
    lines.extend(["", "## 未通过用例", ""])
    if not failures:
        lines.append("所有用例均通过。")
    else:
        for item in failures:
            lines.append(f"### {item['id']} {item['name']}")
            lines.append("")
            lines.append(f"- 分类：{item['category']}")
            lines.append(f"- 严重级别：{item['severity']}")
            lines.append(f"- 实际动作：{item['action'] or '无'}")
            lines.append(f"- 召回条目：{'、'.join(item['retrieved_titles']) or '无'}")
            for check in item["checks"]:
                if not check["passed"]:
                    lines.append(
                        f"- 失败条件 `{check['name']}`：实际 `{check['actual']}`，预期 `{check['expected']}`"
                    )
            lines.append("")

    lines.extend([
        "## 隔离声明",
        "",
        "本报告由固定知识快照和离线模型模式生成。运行期间不会写入业务历史、会话、Agent日志、搜索日志或数据分析统计。",
        "",
    ])
    return "\n".join(lines)


def run_evaluation(live=False, case_ids=None, actual_knowledge=False):
    cases = load_cases()
    if case_ids:
        requested = set(case_ids)
        cases = [case for case in cases if case["id"] in requested]
        missing = sorted(requested - {case["id"] for case in cases})
        if missing:
            raise SystemExit(f"未找到测试用例：{', '.join(missing)}")

    with isolated_backend(live=live, actual_knowledge=actual_knowledge) as backend:
        results = [evaluate_case(case, backend, live=live) for case in cases]

    report = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "mode": (
            "live_actual_knowledge" if live and actual_knowledge
            else "live_isolated" if live
            else "offline_actual_knowledge" if actual_knowledge
            else "offline_isolated"
        ),
        "persistence": False,
        "external_llm": live,
        "summary": build_summary(results),
        "results": results,
    }
    return report


def main():
    parser = argparse.ArgumentParser(description="运行医疗助手隔离标准评估")
    parser.add_argument("--output", help="可选的报告文件名前缀")
    parser.add_argument("--live", action="store_true", help="调用已配置的文字/视觉模型")
    parser.add_argument("--confirm-api-costs", action="store_true", help="确认在线评估可能产生API费用")
    parser.add_argument("--actual-knowledge", action="store_true", help="只读使用正式数据库知识，不使用固定测试快照")
    parser.add_argument("--case", action="append", dest="case_ids", help="只运行指定用例ID，可重复提供")
    args = parser.parse_args()

    if args.live:
        enabled = os.getenv("RUN_LIVE_EVAL", "false").lower() in {"1", "true", "yes"}
        if not enabled or not args.confirm_api_costs:
            raise SystemExit(
                "在线评估需要同时设置 RUN_LIVE_EVAL=true 并提供 --confirm-api-costs。"
            )
        if not args.case_ids:
            raise SystemExit("在线评估必须至少提供一个 --case，避免意外调用全部50条用例。")

    report = run_evaluation(
        live=args.live,
        case_ids=args.case_ids,
        actual_knowledge=args.actual_knowledge,
    )
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = args.output or datetime.now().strftime("evaluation-%Y%m%d-%H%M%S")
    json_path = REPORT_DIR / f"{stamp}.json"
    markdown_path = REPORT_DIR / f"{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(markdown_report(report), encoding="utf-8")

    summary = report["summary"]
    print(f"标准评估完成：{summary['passed']}/{summary['total']} 通过（{summary['pass_rate']}%）")
    print(f"严重失败：{summary['critical_failures']}，重要失败：{summary['important_failures']}")
    print(f"JSON 报告：{json_path}")
    print(f"Markdown 报告：{markdown_path}")


if __name__ == "__main__":
    main()
