FROM node:22-alpine AS base
WORKDIR /app
RUN corepack enable

FROM base AS deps
COPY package.json ./
COPY package-lock.json* pnpm-lock.yaml* yarn.lock* bun.lockb* bun.lock* ./
RUN if [ -f pnpm-lock.yaml ]; then \
      pnpm install --frozen-lockfile; \
    elif [ -f yarn.lock ]; then \
      yarn install --frozen-lockfile; \
    elif [ -f bun.lockb ] || [ -f bun.lock ]; then \
      bun install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then \
      npm ci; \
    else \
      npm install; \
    fi

FROM deps AS builder
COPY . .
ARG NEXT_PUBLIC_API_URL=/api
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
RUN if [ -f pnpm-lock.yaml ]; then \
      pnpm build; \
    elif [ -f yarn.lock ]; then \
      yarn build; \
    elif [ -f bun.lockb ] || [ -f bun.lock ]; then \
      bun run build; \
    else \
      npm run build; \
    fi

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0 \
    NEXT_PUBLIC_API_URL=/api
RUN corepack enable

# This deliberately copies the complete built application for a simple,
# reliable first deployment. It can be optimized later with Next.js standalone output.
COPY --from=builder /app ./

EXPOSE 3000

CMD ["sh", "-c", "if [ -f pnpm-lock.yaml ]; then pnpm start; elif [ -f yarn.lock ]; then yarn start; elif [ -f bun.lockb ] || [ -f bun.lock ]; then bun start; else npm run start; fi"]
