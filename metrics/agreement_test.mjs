// Node check: dictionary formulas (independent JS implementation) reproduce the
// reference vectors from both the TypeScript and Python implementations.
// Run: node metrics/agreement_test.mjs
import fs from 'node:fs';
import assert from 'node:assert/strict';
const here = new URL('.', import.meta.url);
const V = JSON.parse(fs.readFileSync(new URL('vectors.json', here), 'utf8'));
const D = JSON.parse(fs.readFileSync(new URL('dictionary.json', here), 'utf8'));
assert.equal(V.per_hours, D.per_hours);
const num = {
  trir: v => v.deaths + v.dafw_cases + v.djtr_cases + v.other_cases,
  dart: v => v.dafw_cases + v.djtr_cases,
  ltir: v => v.dafw_cases,
  severity: v => v.dafw_days + v.djtr_days,
  fatality: v => v.deaths,
};
const close = (a, b) => (a === null || b === null) ? a === b : Math.abs(a - b) <= 1e-9 * Math.max(Math.abs(a), Math.abs(b), 1e-3);
let n = 0;
for (const v of V.vectors) {
  for (const impl of ['typescript', 'python']) {
    for (const [k, got] of Object.entries(v[impl])) {
      const want = v.hours > 0 ? D.per_hours * num[k](v) / v.hours : null;
      assert.ok(close(want, got), `${v.id} ${impl} ${k}: ${want} vs ${got}`);
      n++;
    }
  }
}
console.log(`ok: ${n} metric values agree`);
