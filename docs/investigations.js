"use strict";
const decisions = {
  records: {
    before:
      "Name the population, period and exposure denominator behind the rate.",
    audit:
      "Rank record influence, vary the screen, and show the trend with and without the influential filings.",
    review:
      "Inspect source records before attributing a change to safety performance. Keep sensitivity separate from corrected truth.",
    url: "https://ehs-osha-analysis.vercel.app/decision-audit.html",
  },
  answers: {
    before:
      "Specify the available evidence, response format and what a scorer pass means.",
    audit:
      "Exhaust the available excerpt responses and inspect examples where the rubric passes an unrelated answer.",
    review:
      "Separate ranking misses from format limits and scoring errors before attributing a score difference to model capability.",
    url: "https://ehs-ai-grounding-eval.vercel.app/evidence-audit.html",
  },
  models: {
    before:
      "State the contrast you want to rank, the measurement model and the uncertainty procedure.",
    audit:
      "Evaluate fit and the contrast test separately, using independent null and alternative simulations.",
    review:
      "Check false positives before calling alternative rejection power. A cutoff learned from a known simulation is not a real-data remedy.",
    url: "https://ehs-risk-sem.vercel.app/model-audit.html",
  },
  meaning: {
    before:
      "Declare the assertions the receiving system must retain, including explicit absences and provenance.",
    audit:
      "Compare the source contract with the exported representation, then reconstruct it and count missing or added assertions.",
    review:
      "Preserve distinctions the export cannot express. A lossless scoped round trip does not validate the source mappings.",
    url: "https://ehs-human-factors-ontology.vercel.app/translation-audit.html",
  },
};
function selectDecision(key, updateUrl = true) {
  const choice = decisions[key];
  if (!choice) return;
  document.querySelectorAll("[data-case]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.case === key));
  });
  for (const stage of ["before", "audit", "review"]) {
    document.getElementById("step-" + stage).textContent = choice[stage];
  }
  document.getElementById("decision-link").href = choice.url;
  if (updateUrl) {
    const url = new URL(location.href);
    url.searchParams.set("decision", key);
    history.replaceState(null, "", url);
  }
}
document.querySelectorAll("[data-case]").forEach((button) => {
  button.addEventListener("click", () => selectDecision(button.dataset.case));
});
selectDecision(
  new URL(location.href).searchParams.get("decision") || "records",
  false,
);
