# Clean Up Current Baseline Drift

## Description

Bring documentation and small debug artifacts back in line with the current Phase 0 implementation.

## Details

The repo has moved beyond some of the older documentation. For example, the frontend README still says point rendering and map click handling are not implemented, even though the map currently fetches points, renders them, and creates points on click.

This ticket keeps the baseline honest before new live-data work begins.

Suggested scope:

- Update stale frontend documentation.
- Update root documentation if it undersells or misstates current behavior.
- Remove temporary debug logging from the frontend entry point.
- Check that local service instructions still match the current Compose setup.
- Keep edits focused on accuracy, not large documentation rewrites.

## Acceptance Criteria

- Documentation accurately describes the current Phase 0 behavior.
- Stale statements about unimplemented point rendering or click handling are removed.
- Temporary debug logging is removed from the app entry point.
- Local run instructions remain clear and accurate.
- No unrelated documentation churn is introduced.
