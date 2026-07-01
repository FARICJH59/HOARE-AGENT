FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json .
RUN npm install

COPY . .
RUN npm run build

# ── Serve the built assets ──────────────────────────────────────────────────
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html

# Proxy /api → backend:8080
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000
