# =============================================================================
# DocPilot AI Frontend Dockerfile
# Multi-stage production build: Node.js compiler -> Nginx high-performance server
# =============================================================================

# Stage 1: Build static assets
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci || npm install

# Copy source and build production bundle
COPY . .
RUN npm run build

# Stage 2: Nginx Web Server
FROM nginx:1.27-alpine AS runtime

# Copy build artifacts to nginx public directory
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration with SPA routing and API reverse-proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
