"""Check the posted tasks and the first bounded Goldbach campaign."""

import json
import math
import unittest
from collections import Counter
from pathlib import Path


GAPS = json.loads(Path(__file__).with_name("gaps.json").read_text(encoding="utf-8"))["gaps"]


class CatalogueTests(unittest.TestCase):
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

    def test_first_certificate_batch_is_independent_and_exact(self):
        # Parse every small block independently of the data used to generate it.
        covered = Counter()
        for gap in GAPS:
            if gap.get("program") != "coverage":
                continue
            shard = gap["shard"]
            lo, hi, index = shard["lo"], shard["hi"], shard["index"]
            if lo > 1000:
                continue
            with self.subTest(gap=gap["id"]):
                self.assertEqual(lo, 4 + 8 * (index - 1))
                self.assertEqual(hi, min(lo + 6, 1000))
                self.assertEqual(gap["id"], f"L-goldbach-coverage-{lo:04d}-{hi:04d}")
                self.assertEqual(gap["imports"], [])
                self.assertEqual(
                    gap["statement"],
                    f"∀ n : ℕ, {lo} ≤ n → n ≤ {hi} → Even n → "
                    "(∃ p q : ℕ, Nat.Prime p ∧ Nat.Prime q ∧ p + q = n)",
                )
                self.assertEqual(gap["plain_statement"]["zh"],
                                 f"闭区间 [{lo}, {hi}] 内的每个偶数都可以写成两个素数之和。")
                self.assertEqual(gap["plain_statement"]["en"],
                                 f"Every even natural number in the closed interval [{lo}, {hi}] "
                                 "is a sum of two primes.")
            covered.update(range(lo, hi + 1, 2))
        self.assertEqual(covered, Counter(range(4, 1001, 2)))

        # Independent smoke check. Only an accepted Actions proof certifies a block.
        primes = {n for n in range(2, 1001) if all(n % d for d in range(2, math.isqrt(n) + 1))}
        sums = {p + q for p in primes for q in primes}
        self.assertFalse(set(covered).difference(sums))


if __name__ == "__main__":
    unittest.main()
