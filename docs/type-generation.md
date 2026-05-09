# API Type Generation Guide

## Overview

This project uses OpenAPI specification to generate TypeScript types from the FastAPI backend, ensuring compile-time type safety for API interactions and eliminating manual type maintenance.

## Architecture

### Backend (Python/FastAPI/Pydantic)

1. **Schema Definitions**: All Pydantic models inherit from `CamelCaseModel` in [backend/app/schemas.py](../backend/app/schemas.py)
2. **Alias Generation**: `to_camel()` function converts snake_case to camelCase for API responses
3. **Configuration**: `populate_by_name=True` allows internal code to use snake_case while API uses camelCase
4. **OpenAPI**: FastAPI automatically generates `/openapi.json` from Pydantic models

### Frontend (TypeScript/React)

1. **Generated Types**: [types.generated.ts](../frontend/src/services/api/types.generated.ts) is created by `openapi-typescript` CLI
2. **Type Helpers**: [type-helpers.ts](../frontend/src/services/api/type-helpers.ts) extracts clean aliases from generated types
3. **Public API**: [types.ts](../frontend/src/services/api/types.ts) re-exports types for component consumption
4. **React Query**: [queries.ts](../frontend/src/services/api/queries.ts) uses generated types for API calls

## Workflow

### Adding a New API Endpoint

1. **Define Pydantic models** in [backend/app/schemas.py](../backend/app/schemas.py):
   ```python
   class UserResponse(CamelCaseModel):
       id: int
       username: str = Field(description="User's display name")
       created_at: datetime = Field(description="Account creation timestamp")
   ```

2. **Add FastAPI route** in [backend/app/main.py](../backend/app/main.py):
   ```python
   @app.get("/users/{user_id}")
   def get_user(user_id: int, db: DbConnection) -> UserResponse:
       # Implementation
       return UserResponse(id=user_id, username="john", created_at=datetime.now())
   ```

3. **Test the endpoint**:
   ```bash
   curl http://127.0.0.1:8000/users/1
   # {"id": 1, "username": "john", "createdAt": "2024-01-01T00:00:00Z"}
   ```

4. **Regenerate frontend types**:
   ```bash
   cd frontend
   npm run generate:api-types
   ```

5. **Add type helper** in [type-helpers.ts](../frontend/src/services/api/type-helpers.ts):
   ```typescript
   export type UserResponse = components['schemas']['UserResponse'];
   ```

6. **Create React Query hook** in [queries.ts](../frontend/src/services/api/queries.ts):
   ```typescript
   export function useGetUserQuery(userId: number) {
     return useQuery({
       queryKey: ["user", userId],
       queryFn: () => request<UserResponse>(`/users/${userId}`),
     });
   }
   ```

### Modifying Existing Models

1. Update Pydantic model in [backend/app/schemas.py](../backend/app/schemas.py)
2. Regenerate types: `npm run generate:api-types`
3. Fix TypeScript compilation errors in frontend (if any)
4. Update tests if needed
5. Commit backend and frontend changes together

## Best Practices

### DO

- ✅ Use `CamelCaseModel` for all API response models
- ✅ Add `Field` descriptions for better OpenAPI documentation
- ✅ Commit generated types to version control
- ✅ Regenerate types immediately after backend changes
- ✅ Use generated types in React Query hooks
- ✅ Keep type helpers file in sync with generated types

### DON'T

- ❌ Edit `types.generated.ts` manually (changes will be overwritten)
- ❌ Add business logic to Pydantic models (keep them as data classes)
- ❌ Use `any` type when generated types exist
- ❌ Forget to restart backend after schema changes
- ❌ Mix snake_case and camelCase in API responses

## Troubleshooting

### Backend schema not updating

**Problem**: Changes to Pydantic models don't appear in `/openapi.json`

**Solution**:
```bash
# Restart FastAPI server
docker compose restart backend

# Verify schema
curl http://127.0.0.1:8000/openapi.json | python3 -m json.tool
```

### Frontend types out of sync

**Problem**: TypeScript types don't match API responses

**Solution**:
```bash
# Verify backend is running
curl http://127.0.0.1:8000/health

# Regenerate types
cd frontend
npm run generate:api-types

# Check git diff
git diff src/services/api/types.generated.ts
```

### CamelCase not working

**Problem**: API returns snake_case instead of camelCase

**Solution**:
1. Verify model inherits from `CamelCaseModel`
2. Check FastAPI route returns the Pydantic model (not a dict)
3. Test with curl to see actual API response:
   ```bash
   curl -X POST http://127.0.0.1:8000/points \
     -H "Content-Type: application/json" \
     -d '{"lat": 45.0, "lon": -93.0}'
   ```

## Developer Workflow

### When backend schemas change:

1. Start backend: `docker compose up -d backend`
2. Regenerate types: `cd frontend && npm run generate:api-types`
3. Fix any TypeScript errors in frontend
4. Test changes locally
5. Commit backend and frontend changes together

## Advanced Topics

### Custom Type Transformations

If you need to transform generated types:

```typescript
// type-helpers.ts
import type { components } from './types.generated';

// Extract and transform
export type Point = components['schemas']['PointResponse'];

// Add computed fields
export type PointWithDistance = Point & {
  distanceFromOrigin: number;
};
```

### Handling Response/Request Distinction

The backend distinguishes between response and list types:

- **PointResponse**: Full details returned by POST /points (includes `srid`)
- **PointListItem**: Minimal fields returned by GET /points (no `srid`)
- **PointCreate**: Request payload for creating points

This pattern:
- Reduces payload size for list endpoints
- Provides complete data for detail endpoints
- Allows future expansion without breaking existing list consumers

## Example: Current API Types

### Backend Schema (Python)

```python
class PointCreate(CamelCaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)

class PointResponse(CamelCaseModel):
    id: int
    lat: float
    lon: float
    srid: int  # Spatial Reference System ID

class PointListItem(CamelCaseModel):
    id: int
    lat: float
    lon: float  # No srid for efficiency
```

### Generated TypeScript Types

```typescript
export interface components {
  schemas: {
    PointCreate: {
      lat: number;
      lon: number;
    };
    PointResponse: {
      id: number;
      lat: number;
      lon: number;
      srid: number;
    };
    PointListItem: {
      id: number;
      lat: number;
      lon: number;
    };
  };
}
```

### Type Helper Aliases

```typescript
export type PointCreate = components['schemas']['PointCreate'];
export type PointResponse = components['schemas']['PointResponse'];
export type PointListItem = components['schemas']['PointListItem'];

// Legacy compatibility
export type Point = PointListItem;
export type CreatePointPayload = PointCreate;
```

### Usage in React Query

```typescript
// Create mutation returns full response
export function useCreatePointMutation() {
  return useMutation({
    mutationFn: (payload: CreatePointPayload) =>
      request<PointResponse>("/points", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  });
}

// List query returns minimal items
export function useGetPointsQuery() {
  return useQuery({
    queryFn: () => request<Point[]>("/points"),
  });
}
```

## Future Enhancements

- **CI Validation**: Automated checks that types are up-to-date
- **Runtime Validation**: Validate API responses match generated types using Zod
- **Type-Safe Client**: Use openapi-fetch for fully typed API client
- **Pre-commit Hooks**: Warn when schemas change without regenerating types
- **Multiple Environments**: Support generating types from staging/production APIs
