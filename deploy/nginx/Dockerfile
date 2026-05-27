FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
ENV VITE_API_BASE_URL=/api
RUN npm run build

FROM nginx:1.27-alpine

COPY deploy/nginx/gateway.conf /etc/nginx/nginx.conf

# Take /app/frontend/dist from the Docker build stage named frontend-build,
# and copy it into /usr/share/nginx/html in the final nginx image.
COPY --from=frontend-build /app/frontend/dist /usr/share/nginx/html

EXPOSE 80
