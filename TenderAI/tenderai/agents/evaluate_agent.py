import json
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
from tenderai.schemas import (
    ProposalEvaluation,
    RequirementsDoc,
    MandatoryGateResult,
    RequirementScore,
)

CHUNK_SIZE = 15


class EvaluateAgent:
    SCORE_CAPS       = {0: 100.0, 1: 75.0, 2: 60.0}
    DEFAULT_CAP      = 40.0
    TYPE_WEIGHTS     = {"mandatory": 3.0, "integration": 2.0, "technical": 1.5, "functional": 1.0, "delivery": 0.8}
    PRIORITY_WEIGHTS = {"High": 3.0, "Medium": 2.0, "Low": 1.0}

    def __init__(self, openai_api_key: str, model: str):
        self.client = OpenAI(api_key=openai_api_key)
        self.model  = model

    def evaluate_proposal(
        self,
        vendor_name: str,
        requirements_doc: RequirementsDoc,
        proposal_text: str,
    ) -> ProposalEvaluation:
        raw_scores     = self._run_llm_evaluation(vendor_name, requirements_doc, proposal_text)
        mandatory_gate = self._compute_mandatory_gate(raw_scores, requirements_doc)
        raw_score      = self._compute_weighted_score(raw_scores, requirements_doc)
        cap            = self.SCORE_CAPS.get(len(mandatory_gate.failures), self.DEFAULT_CAP)
        final_score    = min(raw_score, cap)

        return ProposalEvaluation(
            vendor_name      = vendor_name,
            mandatory_gate   = mandatory_gate,
            match_percentage = round(final_score, 1),
            raw_score        = round(raw_score, 1),
            scores           = raw_scores,
            summary          = self._build_summary(vendor_name, mandatory_gate, raw_score, final_score, raw_scores),
            recommendation   = self._get_recommendation(mandatory_gate, final_score),
        )

    def _run_llm_evaluation(self, vendor_name, requirements_doc, proposal_text):
        reqs = requirements_doc.requirements
        chunks = [reqs[i:i + CHUNK_SIZE] for i in range(0, len(reqs), CHUNK_SIZE)]
        results = [None] * len(chunks)
        with ThreadPoolExecutor(max_workers=len(chunks)) as ex:
            futures = {ex.submit(self._evaluate_chunk, vendor_name, chunk, proposal_text, i, len(chunks)): i for i, chunk in enumerate(chunks)}
            for f in as_completed(futures):
                results[futures[f]] = f.result()
        return [s for chunk in results for s in chunk]

    def _evaluate_chunk(self, vendor_name, requirements, proposal_text, chunk_index, total_chunks):
        system = f"""You are a strict procurement evaluator. Chunk {chunk_index + 1} of {total_chunks}.

Before scoring each requirement, scan the ENTIRE proposal — executive summary,
architecture, compliance matrix, tech stack table, security section.
The compliance matrix is authoritative for mandatory requirements.
Base your decision on ALL mentions found, not just the first.

Evaluation rules:
1. FUTURE COMMITMENT FAILS: "will assess", "TBD", "post-award", "planned",
   "will implement", "roadmap" → met=false (failure_reason: FUTURE_COMMITMENT)
   Exception: delivery requirements may use future tense if a specific plan exists.

2. VERSION MISMATCH FAILS: TLS 1.2 ≠ TLS 1.3, AES-128 ≠ AES-256,
   99.5% ≠ 99.9%, 2 references ≠ 3 references → met=false (VERSION_MISMATCH)

3. OPTIONAL ≠ ENFORCED: MFA optional/add-on does not satisfy MFA enforced
   by default → met=false (OPTIONAL_NOT_ENFORCED)

4. BATCH ≠ REAL-TIME: Scheduled/daily/CSV does not satisfy real-time API
   requirement → met=false (INTEGRATION_MODE_MISMATCH)

5. CLOUD PROVIDER CERT ≠ VENDOR CERT: AWS/Azure/GCP ISO cert is not the
   vendor's own certification → met=false (MISSING_DOCUMENT)

6. EXPIRED CERT FAILS: Certificate dated 3+ years before submission is
   expired → met=false (VERSION_MISMATCH)

7. WRONG GEOGRAPHY FAILS: Data hosted outside the required region fails
   residency requirements → met=false (WRONG_GEOGRAPHY)

8. VAGUE = FALSE: "We are compliant", "we support this" with no specifics
   → met=false (VAGUE_CLAIM)

9. MISSING DOCUMENT: "Available on request" / "can provide post-award"
   → met=false (MISSING_DOCUMENT)

Return JSON only:
{{
  "scores": [
    {{
      "requirement_id": "R1",
      "requirement_type": "mandatory",
      "met": true,
      "confidence": 0.95,
      "justification": "Which sections checked, then conclusion.",
      "failure_reason": null,
      "evidences": [{{"quote": "exact text", "location": "section name"}}]
    }}
  ]
}}"""

        resp = self.client.chat.completions.create(
            model    = self.model,
            messages = [
                {"role": "system", "content": system},
                {"role": "user",   "content": json.dumps({
                    "vendor_name":   vendor_name,
                    "requirements":  [r.model_dump() for r in requirements],
                    "proposal_text": proposal_text,
                })},
            ],
            temperature     = 0.0,
            response_format = {"type": "json_object"},
        )

        content = resp.choices[0].message.content.strip()
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            start, end = content.find("{"), content.rfind("}")
            if start == -1 or end == -1:
                raise ValueError(f"Could not parse JSON (chunk {chunk_index}).")
            data = json.loads(content[start:end + 1])

        return [
            RequirementScore(
                requirement_id   = s["requirement_id"],
                requirement_type = s.get("requirement_type", "functional"),
                met              = bool(s["met"]),
                confidence       = float(s.get("confidence", 0.5)),
                justification    = s.get("justification", ""),
                failure_reason   = s.get("failure_reason"),
                evidences        = [
                    {"quote": e.get("quote", ""), "location": e.get("location", "")}
                    for e in s.get("evidences", [])
                ],
            )
            for s in data.get("scores", [])
        ]

    def _compute_mandatory_gate(self, scores, requirements_doc):
        type_map   = {r.id: r.type for r in requirements_doc.requirements}
        failed_ids = [
            s.requirement_id for s in scores
            if type_map.get(s.requirement_id, s.requirement_type) == "mandatory"
            and not s.met
        ]
        cap = self.SCORE_CAPS.get(len(failed_ids), self.DEFAULT_CAP)
        return MandatoryGateResult(passed=len(failed_ids) == 0, failures=failed_ids, score_cap=cap)

    def _compute_weighted_score(self, scores, requirements_doc):
        type_map     = {r.id: r.type     for r in requirements_doc.requirements}
        priority_map = {r.id: r.priority for r in requirements_doc.requirements}
        total, earned = 0.0, 0.0
        for s in scores:
            w = (self.TYPE_WEIGHTS.get(type_map.get(s.requirement_id, "functional"), 1.0)
                 * self.PRIORITY_WEIGHTS.get(priority_map.get(s.requirement_id, "Medium"), 1.0))
            total += w
            if s.met:
                earned += w * s.confidence
        return round((earned / total) * 100.0, 1) if total else 0.0

    def _get_recommendation(self, gate, final_score):
        if len(gate.failures) >= 2: return "REJECT"
        if len(gate.failures) == 1 or final_score < 70: return "SEEK CLARIFICATION"
        if final_score >= 85: return "AWARD"
        return "SEEK CLARIFICATION"

    def _build_summary(self, vendor_name, gate, raw_score, final_score, scores):
        failed    = [s for s in scores if not s.met]
        met_count = len(scores) - len(failed)
        lines = [
            f"{vendor_name} scored {final_score}% (raw: {raw_score}%).",
            f"Met {met_count} of {len(scores)} requirements.",
        ]
        if gate.failures:
            lines.append(f"Mandatory failures ({len(gate.failures)}): {', '.join(gate.failures)}. Score capped at {gate.score_cap}%.")
        else:
            lines.append("All mandatory requirements passed.")
        if failed:
            lines.append(f"Key gaps: {', '.join(s.requirement_id for s in failed[:5])}.")
        return " ".join(lines)