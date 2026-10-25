# RETROSPECTIVE.md

## What went well?
- The team followed the full workflow: Issue, branch, implementation, test, pull request, review, CI, merge.
- Automated tests (pytest) and Ruff in GitHub Actions caught problems before merging.
- Booking validation rules (FR-03) were tested with Equivalence Partitioning and Boundary Value Analysis.
- Splitting work into modules (accounts, equipment, booking, validation, approval) let members work in parallel.

## What caused difficulties?
- Merge conflicts in shared files (`app/__init__.py`, `app/models.py`, templates) when several branches changed them.
- Overlapping work on the equipment feature led to duplicated template blocks and a failing CI test job that needed a fix.
- Some members were new to Git branching, so early commits and pull requests needed guidance.

## What would our group do differently next time?
- Agree on shared files (models, base template) at the start and merge into `Development` more often.
- Create issues and assign owners before coding so two people do not build the same feature.
- Keep pull requests small and review them the same day.
- Write test cases for each rule before implementing it.

## Metrics
| Metric | Value |
|---|---|
| Issues completed | 36 |
| Pull requests merged | 27 |
| Peer reviews performed | 27 |
| Final test coverage | 97% (156 tests passing) |