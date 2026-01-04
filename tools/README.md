# Development Tools

This directory contains development and testing tools for pulse-backend.

## Postman

API testing collections are located in the `postman/` directory at the repository root.

### Quick Start

1. Install Postman: https://www.postman.com/downloads/
2. Import collections from `postman/` directory
3. Start the application: `make up`
4. Test endpoints in Postman

See [postman/README.md](../postman/README.md) and [doc/guides/postman-setup.md](../doc/guides/postman-setup.md) for detailed usage.

## Future Tools

This directory can be extended with:

- **scripts/** - Development helper scripts
  - Database seeders
  - Test data generators
  - Local setup automation

- **mock-servers/** - Mock external services
  - Mock broker API
  - Mock exchange API

- **load-testing/** - Performance testing tools
  - k6 scripts
  - JMeter configurations

- **monitoring/** - Local monitoring setup
  - Prometheus configuration
  - Grafana dashboards

## See Also

- [Deployment Tools](../deployment/) - Production deployment files
- [Testing Guide](../TESTING.md) - Automated testing
- [API Contracts](../doc/contract/) - API specifications

