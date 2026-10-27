"""Cross-implementation agreement test for the programme metric dictionary.

Checks, using only the standard library:
  1. vectors.json holds outputs of the real TypeScript (ehs-benchmarks) and
     Python (ehs-osha-analysis) implementations; they agree to 1e-9 relative.
  2. An independent reference implementation of dictionary.json formulas
     reproduces both.
  3. Undefined (zero hours) is null in TS and NaN->null in Python, never 0.
  4. Every metric in the dictionary has a formula, columns and CFR citations.
Run: python3 metrics/agreement_test.py
"""
import json, math, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
D = json.loads((HERE / "dictionary.json").read_text())
V = json.loads((HERE / "vectors.json").read_text())
BASIS = D["per_hours"]


def ref(metric, v):
    num = {"trir": v["deaths"] + v["dafw_cases"] + v["djtr_cases"] + v["other_cases"],
           "dart": v["dafw_cases"] + v["djtr_cases"], "ltir": v["dafw_cases"],
           "severity": v["dafw_days"] + v["djtr_days"], "fatality": v["deaths"]}[metric]
    return BASIS * num / v["hours"] if v["hours"] > 0 else None


def close(a, b):
    if a is None or b is None:
        return a is None and b is None
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)


class Agreement(unittest.TestCase):
    def test_basis(self):
        self.assertEqual(BASIS, V["per_hours"])

    def test_ts_python_agree(self):
        for v in V["vectors"]:
            for k, p in v["python"].items():
                self.assertTrue(close(v["typescript"][k], p), (v["id"], k))

    def test_reference_matches_both(self):
        for v in V["vectors"]:
            for k, t in v["typescript"].items():
                self.assertTrue(close(ref(k, v), t), (v["id"], k, "ts"))
            for k, p in v["python"].items():
                self.assertTrue(close(ref(k, v), p), (v["id"], k, "py"))

    def test_zero_hours_is_null_not_zero(self):
        z = [v for v in V["vectors"] if v["hours"] == 0]
        self.assertTrue(z)
        for v in z:
            self.assertTrue(all(x is None for x in v["typescript"].values()))
            self.assertTrue(all(x is None for x in v["python"].values()))

    def test_ratio_of_sums_differs_from_mean_of_rates(self):
        vs = [v for v in V["vectors"] if v["hours"] > 0]
        cases = sum(v["deaths"] + v["dafw_cases"] + v["djtr_cases"] + v["other_cases"] for v in vs)
        pooled = BASIS * cases / sum(v["hours"] for v in vs)
        mean = sum(ref("trir", v) for v in vs) / len(vs)
        self.assertFalse(math.isclose(pooled, mean, rel_tol=1e-3))

    def test_dictionary_complete(self):
        ids = {m["id"] for m in D["metrics"]}
        self.assertEqual(ids, {"trir", "dart", "ltir", "severity", "fatality"})
        for m in D["metrics"]:
            self.assertTrue(m["formula"] and m["form_300a_columns"])
            self.assertTrue(all(c.startswith("29 CFR 1904.") for c in m["cfr"]) and m["cfr"], m["id"])
        doc = (HERE / "DICTIONARY.md").read_text()
        for m in D["metrics"]:
            self.assertIn(m["formula"], doc)
            for c in m["cfr"]:
                self.assertIn(c, doc)


if __name__ == "__main__":
    unittest.main()
