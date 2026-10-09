FROM node:22-slim AS deps
WORKDIR /srv
COPY apps/web/package.json apps/web/package-lock.json* ./
RUN npm install

FROM node:22-slim AS builder
WORKDIR /srv
COPY --from=deps /srv/node_modules ./node_modules
COPY apps/web ./
RUN npm run build

FROM node:22-slim AS runner
WORKDIR /srv
ENV NODE_ENV=production
COPY --from=builder /srv/public ./public
COPY --from=builder /srv/.next ./.next
COPY --from=builder /srv/node_modules ./node_modules
COPY --from=builder /srv/package.json ./package.json

EXPOSE 3000
CMD ["npm", "start"]
