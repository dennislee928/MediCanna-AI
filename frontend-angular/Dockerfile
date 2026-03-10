# MediCanna AI - Angular 前端 (Nginx 靜態資源, Port 80)
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npx ng build --configuration=production

FROM nginx:alpine
COPY --from=builder /app/dist/frontend-angular/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.d/40-gateway-config.sh /docker-entrypoint.d/40-gateway-config.sh
EXPOSE 80
HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
