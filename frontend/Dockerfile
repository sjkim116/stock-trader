# Multi-stage build for the frontend SPA.
#
# Stage 1 builds the static bundle with Vite. Stage 2 serves it with
# nginx, which also reverse-proxies /api/* to the user-api container
# so the browser never needs to know the backend URL. Same image runs
# behind a Caddy/ALB on cloud and direct on port 80 for the personal
# stack.

# Stage 1: build
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci || npm install

COPY . .
RUN npm run build

# Stage 2: serve
FROM nginx:1.27-alpine

# Remove the default site; we ship our own.
RUN rm -f /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/algotrader.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q -O- http://localhost/ >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]
