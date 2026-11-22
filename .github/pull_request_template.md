## What this changes

<!-- One or two sentences. -->

Closes #

## Requirements / defects

<!-- FR-/NFR-/QR- ids, or INS-/BB-DEF-/REV- ids this PR addresses. Update the RTM in the same PR if they change. -->

## Test evidence

- [ ] A failing test was committed before the change that makes it pass (or: explain why not)
- [ ] `ruff check .` and `ruff format --check .` pass
- [ ] `pylint pipeline --fail-under=9.9` passes
- [ ] `pytest` passes; core coverage still at least 60 %

## Reviewer checklist

- [ ] I am not the author of this PR
- [ ] I ran the tests or read the CI log
- [ ] Names, error handling and docstrings follow the conventions in `docs/sqap.md` §5
