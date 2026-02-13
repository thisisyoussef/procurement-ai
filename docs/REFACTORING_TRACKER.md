# Refactoring Tracker

## Status Legend
- `todo`
- `in_progress`
- `done`

## Work Items
1. `done` - Add root architecture and module map docs.
2. `done` - Add backend folder-level responsibility docs.
3. `done` - Add frontend folder-level responsibility docs.
4. `done` - Add tests and migrations folder-level docs.
5. `todo` - Extract repeated backend helper patterns into shared utility modules.
6. `todo` - Reduce duplicated supplier filtering/exclusion logic across scheduler/outreach.
7. `todo` - Standardize API error payload helpers.
8. `todo` - Add contract drift checks between backend schemas and frontend types.
9. `todo` - Add golden-path smoke tests for landing -> product -> outreach flow.
10. `todo` - Publish incident runbook for email delivery failures and queue recovery.

## Validation Checklist (run per refactor batch)
1. `pytest`
2. `cd frontend && npm run build`
3. Manual API sanity check: health, create project, status polling, outreach approval
