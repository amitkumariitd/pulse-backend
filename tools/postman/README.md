# Postman Collection for Pulse Backend

This directory contains Postman collections for testing the Pulse Backend API.

## Setup

1. **Install Postman**
   - Download from https://www.postman.com/downloads/

2. **Import Collection**
   - Open Postman
   - Click "Import" button
   - Select `pulse-backend.postman_collection.json`

3. **Configure Environment**
   - The collection uses a variable `{{base_url}}`
   - Default: `http://localhost:8000`
   - For Docker: Use `http://localhost:8000`
   - For staging: Update to your staging URL
   - For production: Update to your production URL

## Usage

### Local Development (Docker)

1. Start the application:
   ```bash
   # From repository root
   make up

   # Or with docker-compose
   docker-compose -f deployment/docker/docker-compose.yml up
   ```

2. In Postman, set environment variable:
   - `base_url` = `http://localhost:8000`

3. Test endpoints:
   - Health Checks → Main Health Check
   - Health Checks → GAPI Health Check
   - Health Checks → Pulse Health Check
   - GAPI Endpoints → GAPI Hello
   - Pulse Endpoints → Pulse Hello

### Testing Workflow

1. **Health Checks First**
   - Always start with health checks to verify services are running

2. **Test GAPI Endpoints**
   - Test public-facing API endpoints
   - Verify request/response formats

3. **Test Pulse Endpoints**
   - Test internal service endpoints
   - Verify order processing logic

## Adding New Endpoints

When adding new endpoints to the API:

1. Update the API contract in `doc/contract/`
2. Implement the endpoint
3. Add the endpoint to this Postman collection
4. Test using Postman
5. Add automated tests in `tests/`

## Environment Variables

You can create Postman environments for different deployment targets:

- **Local**: `http://localhost:8000`
- **Staging**: `https://stage.yourdomain.com`
- **Production**: `https://yourdomain.com`

## See Also

- API Contracts: `../../doc/contract/`
- Testing Guide: `../../TESTING.md`
- Deployment Guide: `../../doc/deployment.md`
- Docker Files: `../../deployment/docker/`

