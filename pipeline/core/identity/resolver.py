"""Fuse match signals into account links with calibrated confidence (FR-08, FR-09)."""

from pipeline.core.errors import ResolutionError
from pipeline.core.identity.signals import CrossLinkSignal, EmailSignal, HandleSignal, MatchSignal, NameSignal
from pipeline.core.models import AccountLink, AccountRef, CandidateProfile

# (signal, weight). A weight is the confidence that signal gives on its own when it fully fires,
# so with the 0.50 threshold an identical name alone (0.5) or identical handle alone (0.6) links.
DEFAULT_SIGNALS = [
    (EmailSignal(), 0.9),
    (CrossLinkSignal(), 0.9),
    (NameSignal(), 0.5),
    (HandleSignal(), 0.6),
]


def _label(ref: AccountRef) -> str:
    return ref.source if ref.source == "resume" else f"{ref.source}:{ref.handle}"


class IdentityResolver:
    """Links accounts to the candidate. Confidence >= threshold is linked; below it is not (FR-09)."""

    def __init__(self, signals: list[tuple[MatchSignal, float]] | None = None, threshold: float = 0.50):
        signals = DEFAULT_SIGNALS if signals is None else list(signals)
        if not signals or any(not 0.0 <= weight <= 1.0 for _, weight in signals):
            raise ResolutionError("signals must be a non-empty list with weights in [0, 1]")
        if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not 0.0 <= threshold <= 1.0:
            raise ResolutionError("threshold must be a number in [0, 1]", context={"threshold": threshold})
        self._signals = signals
        self._threshold = float(threshold)

    def _compare(self, a: AccountRef, b: AccountRef) -> tuple[float, list[str]]:
        """Noisy-OR over signals: 1 - prod(1 - weight * score). Returns (confidence, fired reasons)."""
        miss = 1.0
        fired = []
        for signal, weight in self._signals:
            result = signal.score(a, b)
            if result.score > 0:
                miss *= 1.0 - weight * result.score
                fired.append(f"{result.signal} ({result.score:.2f}) on {_label(a)}~{_label(b)}: {result.reason}")
        return round(1.0 - miss, 4), fired

    def resolve(
        self, candidate_id: str, run_id: str, anchor: AccountRef, accounts: list[AccountRef]
    ) -> CandidateProfile:
        direct = [self._compare(anchor, account) for account in accounts]
        anchored = [i for i, (confidence, _) in enumerate(direct) if confidence >= self._threshold]
        links = []
        for i, account in enumerate(accounts):
            confidence, rationale = direct[i]
            for j in anchored:  # one hop through an account already linked to the anchor
                if j != i:
                    hop_confidence, hop_reasons = self._compare(accounts[j], account)
                    # A chain is no stronger than its weakest link: cap by the hop account's own confidence (INS-09).
                    confidence = max(confidence, min(hop_confidence, direct[j][0]))
                    rationale = rationale + hop_reasons
            links.append(self._link(candidate_id, run_id, account, confidence, rationale))
        return CandidateProfile(candidate_id, tuple(links))

    def _link(self, candidate_id, run_id, account, confidence, rationale) -> AccountLink:
        linked = confidence >= self._threshold  # exactly at the threshold counts as linked
        if not rationale:
            rationale = ["no matching signals"]
        if not linked:
            rationale = [*rationale, f"below threshold {self._threshold:.2f} — not linked"]
        return AccountLink(candidate_id, run_id, account.source, account.handle, confidence, linked, tuple(rationale))
