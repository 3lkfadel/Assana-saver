FROM caddy:2.11.4-alpine

# curl for the health check; OS security updates (bump to rebuild the layer).
ARG APK_SECURITY_PATCH=2026-10-09
RUN echo "apk-security-patch ${APK_SECURITY_PATCH}" && apk upgrade --no-cache --available && apk add --no-cache curl

COPY Caddyfile /etc/caddy/Caddyfile

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
  CMD curl -fsS -o /dev/null http://127.0.0.1:80/ || exit 1
