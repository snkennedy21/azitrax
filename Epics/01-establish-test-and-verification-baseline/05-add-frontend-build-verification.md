# Add Frontend Build Verification

## Description

Establish the frontend build/typecheck command as the baseline verification step for the React/OpenLayers app.

## Details

The frontend already has a Vite/TypeScript setup and generated API types. Before adding live polling and entity rendering, confirm that the current frontend can be checked consistently.

This ticket does not need to introduce a frontend unit test runner unless there is an obvious lightweight fit. The immediate goal is to make `npm run build` or an equivalent command a documented confidence check.

Suggested scope:

- Run the existing frontend build command.
- Fix any current build/typecheck issues if present.
- Confirm generated API types participate in the build.
- Document the frontend verification command.
- Note any future test runner decision as a follow-up rather than blocking this ticket.

## Acceptance Criteria

- The frontend has a documented verification command.
- The verification command checks TypeScript compilation.
- The verification command succeeds on the current codebase.
- Generated API types are included in the verification path.
- Any decision to defer frontend unit/component tests is documented.
