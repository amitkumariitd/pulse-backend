# Deployment

This directory contains all deployment-related files for pulse-backend.

## Structure

```
deployment/
├── README.md              # This file
├── docker/                # Docker-related files
│   ├── Dockerfile         # Multi-stage Docker build
│   ├── .dockerignore      # Docker build context exclusions
│   ├── docker-compose.yml # Development environment
│   ├── docker-compose.test.yml # Test environment
│   └── init-db.sql        # Database initialization
└── scripts/               # Deployment scripts
    ├── deploy-stage.sh    # Deploy to staging
    └── deploy-prod.sh     # Deploy to production
```

## Quick Start

### Local Development

```bash
# From repository root
make up

# Or directly with docker-compose
docker-compose -f deployment/docker/docker-compose.yml up
```

### Run Tests

```bash
# From repository root
make test

# Or directly with docker-compose
docker-compose -f deployment/docker/docker-compose.test.yml up --abort-on-container-exit
```

### Build Production Image

```bash
# From repository root
make prod-build

# Or directly with docker
docker build -t pulse-backend:latest --target production -f deployment/docker/Dockerfile .
```

## Deployment

### Staging

Automatically deployed when pushing to `develop` branch:

```bash
git push origin develop
```

Or manually:

```bash
./deployment/scripts/deploy-stage.sh
```

### Production

Automatically deployed when pushing to `main` branch:

```bash
git push origin main
```

Or manually:

```bash
./deployment/scripts/deploy-prod.sh
```

## Docker Images

### Build Stages

1. **base** - Python 3.11 + system dependencies + Python packages
2. **development** - Adds dev tools (pytest, etc.) + hot reload
3. **production** - Minimal, optimized, non-root user

### Image Registry

Images are pushed to GitHub Container Registry (ghcr.io):
- `ghcr.io/amitkumariitd/pulse-backend:latest`
- `ghcr.io/amitkumariitd/pulse-backend:main-<sha>`
- `ghcr.io/amitkumariitd/pulse-backend:develop-<sha>`

## Environment Variables

All environment variables are defined in `config/settings.py`.

### Development (docker-compose.yml)

Environment variables are set directly in the compose file.

### Production

Environment variables must be provided at runtime:
- Via ECS task definition
- Via Kubernetes ConfigMap/Secret
- Via environment variables in deployment script

## Future Additions

This directory is structured to accommodate:

- **kubernetes/** - Kubernetes manifests (deployments, services, ingress)
- **terraform/** - Infrastructure as Code (AWS resources, networking)
- **helm/** - Helm charts for Kubernetes deployments
- **ansible/** - Configuration management playbooks

## See Also

- [Deployment Guide](../doc/deployment.md) - Detailed deployment documentation
- [Configuration Standard](../doc/guides/config.md) - Environment configuration
- [Testing Guide](../TESTING.md) - Testing procedures
- [Main README](../README.md) - Project overview

