# GitHub Actions Workflows

This directory contains CI/CD workflows for the Ontology Chat project.

## Workflows Overview

### 🔄 CI Pipeline (`ci.yml`)
**Trigger**: Push/PR to main/develop branches

**Jobs**:
1. **Quality Checks**: Code formatting, type checking, security scanning
2. **Unit Tests**: Fast, isolated tests with coverage reporting
3. **Integration Tests**: Tests with Neo4j, OpenSearch services
4. **Performance Tests**: Benchmark tests (main branch only)
5. **Docker Build**: Container image building
6. **Quality Gate**: Overall status verification

### 🚀 CD Pipeline (`cd.yml`)
**Trigger**: Push to main, tags, manual dispatch

**Jobs**:
1. **Build & Push**: Docker image to GitHub Container Registry
2. **Deploy Staging**: Automatic staging deployment
3. **Deploy Production**: Manual/tag-based production deployment
4. **Security Scan**: Container vulnerability scanning
5. **Release Notes**: Automated changelog generation

### 🛡️ Quality Gate (`quality-gate.yml`)
**Trigger**: Pull requests to main/develop

**Verification**:
- Code coverage ≥70%
- Response time <1.5s average
- No security vulnerabilities
- A-grade quality standards (0.900+ score)
- API contract validation

### 🌙 Nightly Operations (`nightly.yml`)
**Trigger**: Daily at 2 AM UTC, manual dispatch

**Operations**:
- Comprehensive test suite with full services
- Load testing against staging
- Security scanning (Bandit, Safety, Semgrep)
- Database maintenance simulation
- Daily operations report generation

## Configuration

### Environment Variables
Required secrets in GitHub repository settings:

```bash
# Container Registry
GITHUB_TOKEN  # Automatic

# Production Deployment
NEO4J_PASSWORD_STAGING
NEO4J_PASSWORD_PRODUCTION
GRAFANA_PASSWORD_STAGING
GRAFANA_PASSWORD_PRODUCTION

# Notifications (optional)
SLACK_WEBHOOK_URL
DISCORD_WEBHOOK_URL
```

### Service Dependencies
Integration tests require:
- Neo4j 5-community
- OpenSearch 2.11.0
- Redis 7-alpine

## Quality Standards

### Performance Targets
- **Response Time**: <1.5s average, <3s maximum
- **Throughput**: >5 requests/second
- **Cache Hit Rate**: >60%
- **Error Rate**: <1%

### Code Quality
- **Coverage**: ≥70% line coverage
- **Security**: No critical vulnerabilities
- **Style**: Black formatting, Ruff linting
- **Type Safety**: Pyright type checking

### A-Grade Quality Calculation
```python
quality_score = (
    (coverage / 100) * 0.4 +           # Relevance (40%)
    ((10 - complexity) / 10) * 0.35 +  # Diversity (35%)
    (3000 / max(response_ms, 1)) * 0.15 +  # Speed (15%)
    (1.0 if security == 0 else 0.8) * 0.1  # Completeness (10%)
)
# Target: ≥0.900 for A-grade
```

## Branch Strategy

### Main Branch (`main`)
- Protected branch requiring PR reviews
- All quality gates must pass
- Automatic staging deployment
- Production deployment on tags

### Develop Branch (`develop`)
- Integration branch for features
- Full CI pipeline runs
- Staging deployment for testing

### Feature Branches (`feature/`)
- Quality gate checks on PRs
- Unit and integration tests required
- No deployment triggers

## Deployment Strategy

### Staging Environment
- **Automatic**: Every push to `main`
- **URL**: `staging.ontology-chat.example.com`
- **Services**: All components with monitoring
- **Data**: Isolated staging database

### Production Environment
- **Trigger**: Git tags (`v*`) or manual dispatch
- **Strategy**: Blue-green deployment
- **Rollback**: Automatic on failure
- **Monitoring**: Full observability stack

## Monitoring & Alerting

### Performance Monitoring
- Response time tracking
- Throughput measurements
- Quality score trending
- Error rate monitoring

### Alerts
- Deployment failures
- Performance degradation (>150% baseline)
- Security vulnerability detection
- Service health check failures

## Usage Examples

### Manual Production Deployment
```bash
# Via GitHub CLI
gh workflow run cd.yml -f environment=production

# Via GitHub UI
Actions → CD Pipeline → Run workflow → Select production
```

### Trigger Nightly Tests
```bash
gh workflow run nightly.yml
```

### View Quality Gate Results
- Automatic PR comments with quality metrics
- Coverage reports in PR checks
- Security scan results in Security tab

## Troubleshooting

### Common Issues

1. **Test Failures**: Check service dependencies in integration tests
2. **Docker Build**: Verify Dockerfile and build context
3. **Quality Gate**: Review coverage and performance metrics
4. **Deployment**: Check environment variables and secrets

### Debug Commands
```bash
# Local test run
pytest tests/ -v

# Local Docker build
docker build -t ontology-chat .

# Local deployment script
./scripts/deploy.sh status
```

## Best Practices

### Pull Requests
1. Keep PRs small and focused
2. Include tests for new features
3. Update documentation if needed
4. Wait for quality gate to pass

### Releases
1. Use semantic versioning (`v1.2.3`)
2. Create release notes
3. Test in staging before production
4. Monitor deployment metrics

### Performance
1. Keep A-grade quality standards
2. Monitor response time trends
3. Optimize based on benchmark results
4. Review nightly performance reports