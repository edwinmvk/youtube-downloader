# Docker + Nginx deployment

This deployment setup uses four containers:

```text
Internet / Browser
        |
        v
     Nginx :80
        |
   +----+----+
   |         |
   v         v
Next.js    Flask
:3000      :5000
              |
              v
       bgutil-provider
             :4416
              |
              v
           YouTube
```

Only Nginx publishes a host port. Docker Compose services communicate by service name on private bridge networks.

## Why this layout

- Nginx is the single public entry point.
- The browser uses `/api/...` on the same origin as the frontend.
- Flask is not exposed directly to the Internet.
- The PO Token provider is not exposed at all.
- Docker service names provide stable internal DNS instead of hard-coded container IP addresses.
- The backend remains at one Gunicorn worker because its async job state is in memory.

## Local Docker prerequisites

Install:

- Docker Desktop on Windows/macOS, or Docker Engine + Compose plugin on Linux.
- Git.
- A copy of the `youtube-downloader` repository.

Verify:

```bash
docker --version
docker compose version
```

## First local Docker run

From the repository root:

```bash
docker compose config
```

This validates the Compose configuration before starting containers.

Create the root Docker environment file:

```text
.env.docker.example -> .env
```

Then build and start:

```bash
docker compose up --build
```

Open:

```text
http://localhost
```

Health check:

```bash
curl http://localhost/api/health
```

Expected:

```json
{"status":"ok"}
```

## Run in the background

```bash
docker compose up -d --build
```

Check containers:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f nginx
```

```bash
docker compose logs -f backend
```

```bash
docker compose logs -f bgutil-provider
```

Stop everything:

```bash
docker compose down
```

## Important frontend setting

The frontend should use:

```env
NEXT_PUBLIC_API_URL=/api
```

Do not use `http://localhost:5000` inside the production frontend bundle. Nginx routes `/api` to the backend container.

## Important backend setting

Inside Docker the backend must use:

```env
POT_PROVIDER_URL=http://bgutil-provider:4416
```

Do not use `127.0.0.1:4416` inside the backend container. In Docker, `127.0.0.1` refers to the backend container itself.

## Why one Gunicorn worker

The async download jobs are stored in memory inside the Flask process. If multiple Gunicorn workers are used, one request can create a job in worker A while a later progress request reaches worker B, where the job does not exist.

Until job state is moved to a shared store such as Redis, use one Gunicorn worker:

```text
gunicorn --workers 1 --threads 4 ...
```

This is a deliberate limitation of the current architecture, not a Docker limitation.

## Production deployment shape

Use a Linux VPS or VM running Docker. A simple production setup is:

```text
Domain DNS
    |
    v
Ubuntu server
    |
 Docker Compose
    |
    +-- nginx
    +-- frontend
    +-- backend
    +-- bgutil-provider
```

Only ports 80 and 443 should be exposed publicly.

## Production steps

1. Provision an Ubuntu LTS server.
2. Point your domain DNS A/AAAA record to the server.
3. Install Docker Engine and the Compose plugin from Docker's official repository instructions.
4. Clone the repository.
5. Create the production `.env` file from `.env.docker.example`.
6. Replace local values such as `FRONTEND_URL` and `NEXT_PUBLIC_API_URL` with the production values required by your domain/reverse-proxy layout.
7. Run `docker compose up -d --build`.
8. Verify `https://your-domain/api/health` through Nginx.
9. Configure HTTPS with a trusted certificate such as Let's Encrypt/Certbot.
10. Change Nginx `server_name` from `_` to your domain.

## HTTPS

For the learning deployment, start with HTTP first. Once the complete Docker stack works, add HTTPS.

A common approach is Certbot with the Nginx integration:

```bash
sudo certbot --nginx -d your-domain.example
```

Before doing this, ensure:

- DNS points to the server.
- Port 80 is reachable from the Internet.
- Nginx is already serving the domain.

## Updating the application

After pushing a new version:

```bash
git pull
docker compose build
docker compose up -d
```

Or:

```bash
docker compose up -d --build
```

Check the logs after an update:

```bash
docker compose logs -f --tail=200 backend
```

## Operational notes

The current backend keeps async jobs and their temporary output paths in memory. A container restart removes all active and completed jobs. This is acceptable for the current learning project but should be redesigned with shared job state/object storage before horizontal scaling.

The current Nginx configuration sets a 500 MB request body limit to match the Flask configuration. If you change `MAX_FILE_SIZE_MB`, update the Nginx `client_max_body_size` value too.

The PO Token provider is intentionally not published to the host. Do not add a `4416:4416` ports mapping in production.
