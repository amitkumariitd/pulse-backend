# Repository Structure

This document describes the organization of the pulse-backend repository.

## Directory Layout

```
pulse-backend/
├── .github/                    # CI/CD workflows
│   └── workflows/
│       └── ci-cd.yml          # GitHub Actions pipeline
│
├── deployment/                 # 🆕 All deployment files
│   ├── README.md              # Deployment overview
│   ├── docker/                # Docker files
│   │   ├── Dockerfile         # Multi-stage build
│   │   ├── .dockerignore      # Build context exclusions
│   │   ├── docker-compose.yml # Development environment
│   │   ├── docker-compose.test.yml # Test environment
│   │   └── init-db.sql        # Database initialization
│   └── scripts/               # Deployment scripts
│       ├── deploy-stage.sh    # Staging deployment
│       └── deploy-prod.sh     # Production deployment
│
├── tools/                      # 🆕 Development tools
│   └── README.md              # Tools overview
│
├── contracts/                  # 🆕 API contracts (git submodule, see contracts/README.md)
│
├── doc/                        # Documentation
│   ├── deployment.md          # 🆕 Deployment guide
│   ├── product_context.md     # Product overview
│   ├── examples/              # Code examples
│   └── guides/                # Repo-specific guides
│       ├── postgres.md        # PostgreSQL setup (backend-specific)
│       ├── zerodha_integration.md
│       ├── pycharm-debug.md
│       ├── postman-setup.md
│       ├── mock_broker_configuration.md
│       └── testing_without_broker.md
│
├── config/                     # Application configuration
│   └── settings.py            # Central settings
│
├── gapi/                       # GAPI service
│   ├── main.py
│   ├── api/
│   ├── clients/
│   └── middlewares/
│
├── pulse/                      # Pulse service
│   └── main.py
│
├── shared/                     # Shared code
│   ├── contract/
│   ├── http/
│   ├── observability/
│   └── utils/
│
├── tests/                      # Tests
│   ├── unit/
│   └── integration/
│
├── .augment/                   # Augment AI rules
│   ├── context.md
│   └── rules/
│
├── Makefile                    # 🔄 Updated with new paths
├── README.md                   # Project overview
├── TESTING.md                  # Testing guide
├── STRUCTURE.md                # This file
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies
├── pytest.ini                  # Pytest configuration
├── .env.common                 # Common environment variables
└── .env.example                # Environment template
```

## Key Changes

### ✅ What Changed

1. **Created `deployment/` directory**
   - Moved all Docker files to `deployment/docker/`
   - Moved deployment scripts to `deployment/scripts/`
   - Added `deployment/README.md`

2. **Created `tools/` directory**
   - Added `tools/README.md` for future development tools
   - Postman collections remain in `postman/` directory

3. **Updated documentation**
   - Renamed `DOCKER.md` → `doc/deployment.md`
   - Updated all file references

4. **Updated automation**
   - Updated `Makefile` with new paths
   - Updated `.github/workflows/ci-cd.yml` with new paths
   - Updated `.dockerignore` to exclude deployment/tools folders

### ✅ What Stayed the Same

- Root-level files: `Makefile`, `README.md`, `TESTING.md`, `main.py`
- Application code: `gapi/`, `pulse/`, `shared/`, `config/`
- Tests: `tests/`
- Documentation: `doc/` (with additions)
- Configuration: `.env.*` files

## Benefits

1. **Clean Root Directory**
   - Only essential files at root level
   - Easy to navigate

2. **Clear Separation**
   - Deployment files isolated
   - Development tools isolated
   - Application code unchanged

3. **Scalable Structure**
   - Room for Kubernetes manifests
   - Room for Terraform/IaC
   - Room for additional tools

4. **Professional Organization**
   - Follows industry standards
   - Easy for new developers
   - Ready for future growth

## Usage

All commands remain the same:

```bash
# Development
make up          # Start services
make down        # Stop services
make logs        # View logs

# Testing
make test        # Run all tests
make test-unit   # Run unit tests
make test-int    # Run integration tests

# Database
make db-shell    # PostgreSQL shell
make db-reset    # Reset database

# Production
make prod-build  # Build production image
```

## See Also

- [Deployment Guide](doc/deployment.md) - Detailed deployment documentation
- [Deployment README](deployment/README.md) - Deployment structure
- [Tools README](tools/README.md) - Development tools
- [Testing Guide](TESTING.md) - Testing procedures
- [Main README](README.md) - Project overview

