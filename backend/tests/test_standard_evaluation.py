import unittest

from backend.tests.evaluation_support import (
    FIXTURE_FILE,
    evaluate_case,
    isolated_backend,
    load_cases,
    load_json,
)


class StandardOfflineEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = isolated_backend()
        cls.backend = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    def test_current_quality_does_not_regress_below_baseline(self):
        baseline_path = FIXTURE_FILE.parent / "baseline_known_failures.json"
        baseline = load_json(baseline_path)
        results = [evaluate_case(case, self.backend) for case in load_cases()]
        failed_ids = {item["id"] for item in results if not item["passed"]}
        known_failures = set(baseline["known_failures"])
        unexpected_failures = sorted(failed_ids - known_failures)
        passed_count = sum(1 for item in results if item["passed"])

        self.assertFalse(
            unexpected_failures,
            f"出现基线之外的新失败：{', '.join(unexpected_failures)}",
        )
        self.assertGreaterEqual(
            passed_count,
            baseline["minimum_passed"],
            f"通过数从基线 {baseline['minimum_passed']} 降至 {passed_count}",
        )


if __name__ == "__main__":
    unittest.main()
