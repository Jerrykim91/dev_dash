FROM node:22-alpine AS build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend ./
COPY shared /app/shared
COPY infra/visual/sync-lobby-manifest.cjs /app/infra/visual/sync-lobby-manifest.cjs
ARG VITE_DEVNEST_URL=
ENV VITE_DEVNEST_URL=$VITE_DEVNEST_URL
RUN npm run build
FROM nginx:1.27-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/dist /usr/share/nginx/html
EXPOSE 80
