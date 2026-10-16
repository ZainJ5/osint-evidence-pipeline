"""Dispatch each claim to the verification rule for its kind (FR-12)."""

from pipeline.core.errors import ScoringError
from pipeline.core.models import Claim, EvidenceNode, Verdict
from pipeline.core.scoring.rules import VerificationRule


class ClaimVerifier:
    """Dispatches each claim to the rule for its kind."""

    def __init__(self, rules: list[VerificationRule]):
        self._rules = {rule.kind: rule for rule in rules}

    def verify_all(self, claims: list[Claim], evidence: list[EvidenceNode], run_id: str) -> list[Verdict]:
        verdicts = []
        for claim in claims:
            rule = self._rules.get(claim.kind)
            if rule is None:
                raise ScoringError(f"no rule for claim kind '{claim.kind}'", context={"claim_id": claim.id})
            verdicts.append(rule.verify(claim, evidence, run_id))
        return verdicts
