# Development Tools

This directory contains development and testing tools for pulse-backend.

## Structure

```
tools/
├── README.md              # This file
└── postman/               # Postman API testing
    ├── README.md
    └── pulse-backend.postman_collection.json
```

## Postman

API testing collection for manual testing and debugging.

### Quick Start

1. Install Postman: https://www.postman.com/downloads/
2. Import collection: `tools/postman/pulse-backend.postman_collection.json`
3. Start the application: `make up`
4. Test endpoints in Postman

See [postman/README.md](postman/README.md) for detailed usage.

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

