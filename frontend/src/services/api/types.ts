export type HealthResponse = {
  status: string;
};

export type Point = {
  id: number;
  lat: number;
  lon: number;
};

export type CreatePointPayload = {
  lat: number;
  lon: number;
};
