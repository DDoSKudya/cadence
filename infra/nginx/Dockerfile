FROM node:22-alpine AS frontend-build

WORKDIR /src/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine

COPY --from=frontend-build /src/frontend/dist /usr/share/nginx/html
COPY infra/nginx/conf.d/prod.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
