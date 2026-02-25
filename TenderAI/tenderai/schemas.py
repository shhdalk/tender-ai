# tenderai/schemas.py

from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class Requirement(BaseModel):
    id: str
    type: Literal["mandatory", "functional", "technical", "integration", "delivery"] = "functional"
    title: str
    description: str
    priority: Literal["High", "Medium", "Low"] = "Medium"
    mandatory_evidence: Optional[str] = None  # what proof vendor must submit
    evaluation_hint: Optional[str] = None     # what a failure looks like


class RequirementsDoc(BaseModel):
    rfp_title: Optional[str] = None
    requirements: List[Requirement]


class Evidence(BaseModel):
    quote: str
    location: str = Field(default="", description="Section/heading if available")


class RequirementScore(BaseModel):
    requirement_id: str
    requirement_type: str = "functional"   # carried over for penalty logic
    met: bool
    confidence: float = Field(ge=0.0, le=1.0)
    justification: str
    failure_reason: Optional[str] = None   # populated for mandatory failures
    evidences: List[Evidence] = Field(default_factory=list)


class MandatoryGateResult(BaseModel):
    passed: bool                           # True only if ALL mandatory reqs pass
    failures: List[str]                    # list of requirement IDs that failed
    score_cap: float                       # max allowed score given failures


class ProposalEvaluation(BaseModel):
    vendor_name: str
    mandatory_gate: MandatoryGateResult
    match_percentage: float = Field(ge=0.0, le=100.0)   # after cap applied
    raw_score: float = Field(ge=0.0, le=100.0)           # before cap
    scores: List[RequirementScore]
    summary: str
    recommendation: Literal["AWARD", "SEEK CLARIFICATION", "REJECT"]