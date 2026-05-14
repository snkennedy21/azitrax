/**
 * Type helper utilities for API types.
 *
 * This file extracts clean type aliases from the generated OpenAPI types,
 * making them easier to import and use throughout the application.
 *
 * These types are generated from the backend OpenAPI schema.
 * To regenerate: npm run generate:api-types
 */

import type { components } from "./types.generated";

// Schema types from OpenAPI components
export type PointCreate = components["schemas"]["PointCreate"];
export type PointResponse = components["schemas"]["PointResponse"];
export type PointListItem = components["schemas"]["PointListItem"];
export type LiveVesselMapItem = components["schemas"]["LiveVesselMapItem"];
export type LiveVesselsMetadata = components["schemas"]["LiveVesselsMetadata"];
export type LiveVesselsResponse = components["schemas"]["LiveVesselsResponse"];

// Health check types (not in schema components, defined manually)
export type HealthResponse = {
  status: string;
};

export type HealthDbResponse = {
  status: string;
  postgis_version: string;
};
