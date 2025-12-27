# Docker Guide for Pulse Backend

Complete guide for local development, testing, debugging, and deployment using Docker.

---

## Prerequisites

- **Docker Desktop** (Mac/Windows) or **Docker Engine** (Linux)
- **Docker Compose** v2.0+
- **Python 3.12+** (for local development without Docker)
- **Git**
- **Postman** (optional, for API testing)

---

## Quick Start

### 1. Start Development Environment

```bash
# Using Makefile (recommended)
make up

# Or using docker-compose directly
docker-compose -f deployment/docker/docker-compose.yml up

# Access the application
curl http://localhost:8000/health
```

**Services started:**
- Application: http://localhost:8000
- PostgreSQL: localhost:5432

**Note:** All Docker files are located in `deployment/docker/`

### 2. Run Tests

```bash
# Run all tests
make test

# Or manually
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

### 3. Debug with Postman

1. Start the application: `make up`
2. Import Postman collection from `tools/postman/pulse-backend.postman_collection.json`
3. Test endpoints in Postman

---

## Development Workflow

### Start Services

```bash
# Start in foreground (see logs)
docker-compose up

# Start in background
docker-compose up -d
make up
```

### View Logs

```bash
# Follow application logs
docker-compose logs -f app
make logs

# View all logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100 app
```

### Hot Reload

Code changes are automatically detected:

1. Edit any Python file
2. Save the file
3. Uvicorn automatically reloads
4. Test the changes immediately

### Stop Services

```bash
# Stop services
docker-compose down
make down

# Stop and remove volumes (clean slate)
docker-compose down -v
make clean
```

---

## Testing

### Run All Tests

```bash
make test
```

### Run Specific Test Types

```bash
# Unit tests only
make test-unit

# Integration tests only
make test-int
```

### Manual Test Execution

```bash
# Start test environment
docker-compose -f docker-compose.test.yml up -d

# Run specific tests
docker-compose -f docker-compose.test.yml exec test python -m pytest tests/unit/test_specific.py -v

# Clean up
docker-compose -f docker-compose.test.yml down -v
```

---

## Database Operations

### Access PostgreSQL Shell

```bash
# Using Makefile
make db-shell

# Or manually
docker exec -it pulse-postgres psql -U pulse -d pulse
```

### Reset Database

```bash
# WARNING: Deletes all data
make db-reset
```

### Run Migrations

```bash
# Access app container
make shell

# Run Alembic migrations
alembic upgrade head
```

---

## Debugging with Postman

### Setup

1. **Import Collection**
   - Open Postman
   - Import `postman/pulse-backend.postman_collection.json`

2. **Configure Environment**
   - Create environment: "Local Docker"
   - Set variable: `base_url` = `http://localhost:8000`

3. **Start Application**
   ```bash
   make up
   ```

### Test Endpoints

1. **Health Checks**
   - Main: `GET /health`
   - GAPI: `GET /gapi/health`
   - Pulse: `GET /pulse/health`

2. **GAPI Endpoints**
   - Hello: `GET /gapi/api/hello`

3. **Pulse Endpoints**
   - Hello: `GET /pulse/internal/hello`

### Debugging Tips

- Check logs: `make logs`
- Verify database: `make db-shell`
- Restart services: `make restart`
- View container status: `make ps`

---

## Production Build

### Build Production Image

```bash
# Build production image
make prod-build

# Or manually
docker build -t pulse-backend:latest --target production .
```

### Test Production Image Locally

```bash
# Run production container
make prod-run

# Stop production container
make prod-stop
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

The `.github/workflows/ci-cd.yml` automatically:

1. **On every push/PR:**
   - Runs unit tests
   - Runs integration tests
   - Generates coverage report
   - Builds Docker image
   - Pushes to GitHub Container Registry (ghcr.io)

2. **On push to `develop`:**
   - Deploys to staging environment

3. **On push to `main`:**
   - Deploys to production environment

### Setup GitHub Actions

1. **Enable GitHub Actions**
   - Already enabled by default

2. **Configure Environments** (Settings → Environments)
   - Create `staging` environment
   - Create `production` environment
   - Add environment protection rules

3. **Add Secrets** (if needed for deployment)
   - AWS credentials
   - SSH keys
   - Database passwords

### Deployment

```bash
# Deploy to staging
git checkout develop
git push origin develop

# Deploy to production
git checkout main
git merge develop
git push origin main
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>
```

### Database Connection Issues

```bash
# Check PostgreSQL status
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Container Won't Start

```bash
# View logs
docker-compose logs app

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

### Tests Failing

```bash
# Check test database
docker-compose -f docker-compose.test.yml logs postgres-test

# Run tests with verbose output
docker-compose -f docker-compose.test.yml run --rm test python -m pytest -vv
```

---

## Makefile Commands Reference

```bash
make help          # Show all available commands
make up            # Start services
make down          # Stop services
make restart       # Restart services
make logs          # View logs
make build         # Build images
make test          # Run all tests
make test-unit     # Run unit tests
make test-int      # Run integration tests
make db-shell      # PostgreSQL shell
make db-reset      # Reset database
make shell         # App container shell
make clean         # Remove all containers/volumes
make ps            # Show running containers
make prod-build    # Build production image
make prod-run      # Run production container
make prod-stop     # Stop production container
```

---

## Best Practices

1. **Always use `make` commands** - Simpler and consistent
2. **Run tests before pushing** - `make test`
3. **Check logs when debugging** - `make logs`
4. **Clean up regularly** - `make clean`
5. **Use Postman for manual testing** - Import collection
6. **Never commit `.env.local`** - Already in .gitignore

---

## File Locations

All deployment files are organized in the `deployment/` directory:

- **Docker files:** `deployment/docker/`
  - `Dockerfile` - Multi-stage build
  - `docker-compose.yml` - Development environment
  - `docker-compose.test.yml` - Test environment
  - `.dockerignore` - Build context exclusions
  - `init-db.sql` - Database initialization

- **Deployment scripts:** `deployment/scripts/`
  - `deploy-stage.sh` - Staging deployment
  - `deploy-prod.sh` - Production deployment

- **CI/CD:** `.github/workflows/ci-cd.yml`

## Next Steps

- See `deployment/README.md` for deployment structure
- See `TESTING.md` for testing guidelines
- See `tools/postman/README.md` for Postman usage
- See `doc/contract/` for API contracts
- See `.augment/context.md` for architecture

