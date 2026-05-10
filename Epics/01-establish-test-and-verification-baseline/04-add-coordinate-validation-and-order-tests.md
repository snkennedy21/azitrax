# Add Coordinate Validation and Order Tests

## Description

Add regression tests that protect latitude/longitude validation and PostGIS coordinate ordering.

## Details

Coordinate ordering is one of the easiest mistakes to make in geospatial systems. The API accepts latitude and longitude as separate fields, while PostGIS stores points as X/Y, which means longitude first and latitude second.

These tests should protect both input validation and storage/readback behavior.

Suggested scope:

- Test invalid latitude values below `-90` and above `90`.
- Test invalid longitude values below `-180` and above `180`.
- Test that valid coordinates are returned with latitude and longitude in the same semantic positions that were submitted.
- Use an asymmetric coordinate pair so reversal would be obvious.
- If possible, assert that the stored geometry has SRID `4326`.

## Acceptance Criteria

- Invalid latitude values return validation errors.
- Invalid longitude values return validation errors.
- A coordinate-order regression test fails if latitude and longitude are reversed.
- At least one test verifies SRID `4326` for a saved point.
- These tests run as part of the normal backend test command.
