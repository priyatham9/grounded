"""Regenerate metrics/vectors.json from the two real implementations.

Usage (needs pandas+numpy and Node >= 22.6, run from the grounded repo root):

    python3 metrics/generate_vectors.py \
        --osha-analysis ../ehs-osha-analysis --benchmarks ../ehs-benchmarks

The TypeScript source (src/rates.ts, types.ts, quality.ts) is copied to a temp
directory with its ``.js`` import suffixes rewritten to ``.ts`` and executed with
``node --experimental-strip-types``; no npm install is needed. The Python side
calls ``ehs_osha.metrics.compute_rates`` on a one-row frame per vector.
The committed vectors.json records the git commit of each repo it was run on.
"""
import argparse, json, math, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
RATES = ["trir", "dart", "ltir", "severity"]

NODE_RUNNER = """
import { trir, dart, ltir, fatalityRate, severityRate } from './rates.ts';
import fs from 'node:fs';
const vs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
console.log(JSON.stringify(vs.map(v => {
  const c = { deaths: v.deaths, daysAwayCases: v.dafw_cases, jobTransferCases: v.djtr_cases,
    otherRecordableCases: v.other_cases, daysAway: v.dafw_days, daysRestricted: v.djtr_days };
  const h = { employeeHours: v.hours };
  return { trir: trir(c, h).value, dart: dart(c, h).value, ltir: ltir(c, h).value,
    severity: severityRate(c, h).value, fatality: fatalityRate(c, h).value };
})));
"""


def git_head(repo: Path) -> str:
    return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()


def run_ts(bench: Path, inputs: list) -> list:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for n in ("rates", "types", "quality"):
            src = (bench / "src" / f"{n}.ts").read_text()
            (td / f"{n}.ts").write_text(re.sub(r"\.js'", ".ts'", src))
        (td / "run.mjs").write_text(NODE_RUNNER)
        (td / "in.json").write_text(json.dumps(inputs))
        out = subprocess.check_output(
            ["node", "--experimental-strip-types", "--no-warnings", str(td / "run.mjs"), str(td / "in.json")],
            text=True)
    return json.loads(out)


def run_py(analysis: Path, inputs: list) -> list:
    sys.path.insert(0, str(analysis / "src"))
    import pandas as pd
    from ehs_osha.metrics import compute_rates
    res = []
    for v in inputs:
        df = pd.DataFrame([{
            "total_deaths": v["deaths"], "total_dafw_cases": v["dafw_cases"],
            "total_djtr_cases": v["djtr_cases"], "total_other_cases": v["other_cases"],
            "total_dafw_days": v["dafw_days"], "total_djtr_days": v["djtr_days"],
            "total_hours_worked": v["hours"], "implausible": False}])
        row = compute_rates(df)
        res.append({k: (None if math.isnan(row[f"{k}_screened"]) else row[f"{k}_screened"]) for k in RATES})
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--osha-analysis", required=True)
    ap.add_argument("--benchmarks", required=True)
    a = ap.parse_args()
    inputs = json.loads((HERE / "vector_inputs.json").read_text())
    ts = run_ts(Path(a.benchmarks), inputs)
    py = run_py(Path(a.osha_analysis), inputs)
    out = {
        "generated_from": {
            "ehs-benchmarks": {"commit": git_head(Path(a.benchmarks)), "function": "src/rates.ts trir/dart/ltir/severityRate/fatalityRate"},
            "ehs-osha-analysis": {"commit": git_head(Path(a.osha_analysis)), "function": "src/ehs_osha/metrics.py compute_rates (*_screened, implausible=False)"},
        },
        "per_hours": 200000,
        "vectors": [dict(v, typescript=t, python=p) for v, t, p in zip(inputs, ts, py)],
    }
    (HERE / "vectors.json").write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {len(inputs)} vectors")

if __name__ == "__main__":
    main()
