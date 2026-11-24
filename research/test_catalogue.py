"""Check the public research queue and the scope of its analytic targets."""

import json
import unittest
from pathlib import Path
from urllib.parse import urlparse


GAPS = json.loads(Path(__file__).with_name("gaps.json").read_text(encoding="utf-8"))["gaps"]
PROBLEMS = json.loads(Path(__file__).with_name("problems.json").read_text(encoding="utf-8"))


class CatalogueTests(unittest.TestCase):
    def test_problem_tasks_have_unique_names_and_respect_scope(self):
        all_gaps = GAPS + [gap for problem in PROBLEMS.values() for gap in problem["gaps"]]
        for key in ("id", "file", "module"):
            values = [gap[key] for gap in all_gaps]
            self.assertEqual(len(values), len(set(values)), key)
        for slug, problem in PROBLEMS.items():
            self.assertRegex(slug, r"^[a-z]+(?:-[a-z]+)*$")
            self.assertTrue(any(gap.get("parallel") is True for gap in problem["gaps"]), slug)
            for gap in problem["gaps"]:
                with self.subTest(problem=slug, gap=gap["id"]):
                    self.assertRegex(gap["id"], rf"^L-{slug}-[a-z0-9]+(?:-[a-z0-9]+)*$")
                    self.assertLessEqual(len(gap["id"]), 64)
                    name = gap["id"].replace("-", "_")
                    self.assertEqual(gap["file"], f"lean/PEqualNP/Outside/{name}.lean")
                    self.assertEqual(gap["module"], f"PEqualNP.Outside.{name}")
                    self.assertIn(gap["program"], {"foundation", "correlation"})
                    for lang in ("en", "zh"):
                        self.assertTrue(gap["plain_statement"][lang].strip())

    def test_lease_ids_and_pr_paths(self):
        for key in ("id", "file", "module"):
            values = [gap[key] for gap in GAPS]
            self.assertEqual(len(values), len(set(values)), key)
        for gap in GAPS:
            with self.subTest(gap=gap["id"]):
                self.assertRegex(gap["id"], r"^L-goldbach-[a-z0-9]+(?:-[a-z0-9]+)*$")
                self.assertLessEqual(len(gap["id"]), 64)
                name = gap["id"].replace("-", "_")
                self.assertEqual(gap["module"], f"PEqualNP.Outside.{name}")
                self.assertEqual(gap["file"], f"lean/PEqualNP/Outside/{name}.lean")
                for lang in ("en", "zh"):
                    self.assertTrue(gap["plain_statement"][lang].strip())

    def test_analytic_programs_and_context(self):
        self.assertEqual({g["program"] for g in GAPS},
                         {"foundation", "grh", "correlation", "exceptions"})
        for gap in GAPS:
            with self.subTest(gap=gap["id"]):
                self.assertNotIn("shard", gap)
                self.assertNotIn("coverage-", gap["id"])
                self.assertTrue(gap["brief"]["zh"].strip())
                self.assertTrue(gap["brief"]["en"].strip())
                source = urlparse(gap["source"])
                self.assertEqual(source.scheme, "https")
                self.assertTrue(source.netloc)
                self.assertIsInstance(gap.get("parallel", False), bool)

    def test_conditional_analytic_claims_preserve_their_inputs(self):
        by_id = {g["id"]: g["statement"] for g in GAPS}
        for suffix in ("rh-zeta-zero-sum", "rh-short-interval-large"):
            self.assertTrue(by_id[f"L-goldbach-{suffix}"].startswith("RiemannHypothesis →"))
        for suffix in ("grh-progression-error", "grh-goldbach-exception-density"):
            claim = by_id[f"L-goldbach-{suffix}"]
            self.assertTrue(claim.startswith("(∀ (Q : ℕ) [NeZero Q]"))
            self.assertIn("DirichletCharacter.LFunction χ s = 0 → s.re = 1 / 2) →", claim)

    def test_final_target_has_all_even_inputs_and_only_prime_weights(self):
        target = next(g for g in GAPS if g["id"] == "L-goldbach-binary-pointwise-positivity")
        self.assertTrue(target["parallel"])
        self.assertEqual(
            target["statement"],
            "∀ n : ℕ, 4 ≤ n → Even n → let w : ℕ → ℝ := fun k => "
            "if Nat.Prime k then Real.log (k : ℝ) else 0; "
            "0 < Finset.sum (Finset.range (n + 1)) (fun p => w p * w (n - p))",
        )


if __name__ == "__main__":
    unittest.main()
