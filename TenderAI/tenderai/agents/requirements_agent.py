# tenderai/agents/requirements_agent.py

import json
from openai import OpenAI
from tenderai.schemas import RequirementsDoc


class RequirementsAgent:
    def __init__(self, openai_api_key: str, model: str):
        self.client = OpenAI(api_key=openai_api_key)
        self.model = model

    def extract_requirements(self, rfp_text: str) -> RequirementsDoc:
        system = """You are a requirements extraction assistant.

Extract every requirement from the RFP. Cover all five types:
- mandatory: pass/fail gates (certifications, residency, references, legal docs)
- functional: what the system must do
- technical: performance, security, architecture constraints
- integration: named external system connections
- delivery: timeline, training, support, documentation

Rules:
1. Use exact numbers from the text (%, seconds, years, counts).
2. For mandatory items, state what evidence the vendor must provide.
3. For integrations, note real-time vs batch and direction if stated — if not stated, leave it out.
4. Do not invent details not in the RFP.
5. Do not duplicate — if two sentences cover the same thing, merge them.
6. Stop when done — do not pad with invented requirements.

Return JSON only:
{
  "rfp_title": "string or null",
  "requirements": [
    {
      "id": "R1",
      "type": "mandatory|functional|technical|integration|delivery",
      "title": "Short title",
      "description": "Specific and testable. Include exact numbers.",
      "priority": "High|Medium|Low",
      "mandatory_evidence": "What the vendor must submit (mandatory only, else null)",
      "evaluation_hint": "What a failure looks like in one sentence"
    }
  ]
}

Priority guide:
- mandatory → always High
- technical/functional that block acceptance → High
- supporting features, reporting → Medium
- nice-to-have → Low
- integrations: High if mandatory, Medium if optional"""

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": f"Extract all requirements from this RFP:\n\n{rfp_text}"},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )

        content = resp.choices[0].message.content.strip()
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            start, end = content.find("{"), content.rfind("}")
            if start == -1 or end == -1:
                raise ValueError("Could not parse JSON from requirements agent.")
            data = json.loads(content[start:end + 1])

        return RequirementsDoc.model_validate(data)