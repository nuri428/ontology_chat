# Production Monitoring Setup

## Overview
Comprehensive production monitoring solution using Prometheus, Grafana, and AlertManager for the Ontology Chat application. This setup provides real-time metrics collection, visualization, and alerting for maintaining A-grade quality (0.900+ score).

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│   Application   │───▶│ Prometheus   │───▶│  Grafana    │
│   (Metrics)     │    │  (Storage)   │    │ (Dashboards)│
└─────────────────┘    └──────────────┘    └─────────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │ AlertManager │
                       │  (Alerts)    │
                       └──────────────┘
```

## Quick Start

### 1. Start Monitoring Stack
```bash
# Run the startup script
./scripts/start-monitoring.sh

# Or manually with docker-compose
docker-compose -f docker-compose.monitoring.yml up -d
```

### 2. Access Dashboards
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/ontology_admin_2024)
- **AlertManager**: http://localhost:9093

### 3. Import Dashboards
Dashboards are automatically provisioned:
- **System Overview**: Main application metrics
- **Cache Performance**: Multi-level cache analytics

## Components

### 🔍 **Prometheus** (Port 9090)
Metrics collection and storage with 30-day retention.

**Key Metrics Collected:**
- HTTP request metrics (rate, duration, errors)
- A-grade quality scores
- Cache performance (hit rates, memory usage)
- Circuit breaker states
- LLM operation timings
- System resources (CPU, memory, disk)

### 📊 **Grafana** (Port 3001)
Visualization and dashboard platform with pre-configured dashboards.

**Default Dashboards:**
1. **System Overview Dashboard**
   - A-grade quality score monitoring
   - Request rate and response time tracking
   - Error rate analysis
   - System resource utilization

2. **Cache Performance Dashboard**
   - Multi-level cache hit rates
   - Memory usage across cache levels
   - Cache operation latencies
   - Cache effectiveness scoring

### 🚨 **AlertManager** (Port 9093)
Alert routing and notification management.

**Alert Categories:**
- **Critical**: Service down, quality degradation
- **Warning**: High latency, low cache hit rates
- **Info**: Unusual request patterns

### 📈 **Node Exporter** (Port 9100)
System metrics collection for host monitoring.

### 🔄 **Redis Exporter** (Port 9121)
Redis cache metrics for L2 cache monitoring.

## Metrics Reference

### Application Metrics

#### Quality Metrics
```
ontology_chat_quality_score                    # A-grade quality score (0-1)
```

#### HTTP Metrics
```
http_requests_total{method,endpoint,status}     # Total HTTP requests
http_request_duration_seconds{method,endpoint} # Request duration histogram
```

#### Cache Metrics
```
ontology_chat_cache_hit_rate                   # Overall cache hit rate
ontology_chat_cache_l1_hit_rate               # L1 memory cache hit rate
ontology_chat_cache_l2_hit_rate               # L2 Redis cache hit rate
ontology_chat_cache_l3_hit_rate               # L3 disk cache hit rate
ontology_chat_cache_l1_memory_usage_bytes     # L1 memory usage
ontology_chat_cache_effectiveness_score       # Cache effectiveness (0-1)
```

#### Circuit Breaker Metrics
```
ontology_chat_circuit_breaker_state{name,state}      # Circuit breaker states
ontology_chat_circuit_breaker_failures_total{name}   # Failure counts
ontology_chat_circuit_breaker_successes_total{name}  # Success counts
```

#### Processing Metrics
```
ontology_chat_llm_duration_seconds{model,operation}        # LLM operation time
ontology_chat_context_duration_seconds{source}             # Context retrieval time
ontology_chat_neo4j_queries_total{status}                  # Neo4j query counts
ontology_chat_opensearch_queries_total{status}             # OpenSearch query counts
```

### System Metrics (Node Exporter)
```
node_cpu_seconds_total        # CPU usage
node_memory_MemAvailable_bytes # Available memory
node_filesystem_avail_bytes   # Available disk space
```

### Redis Metrics (Redis Exporter)
```
redis_up                     # Redis connection status
redis_memory_used_bytes      # Redis memory usage
redis_connected_clients      # Connected clients count
```

## Alert Rules

### Critical Alerts
- **ServiceDown**: API service unavailable (>1 minute)
- **QualityScoreDegradation**: Quality below 0.900 (>5 minutes)
- **RedisDown**: Redis L2 cache unavailable (>30 seconds)
- **Neo4jDown**: Neo4j database unavailable (>1 minute)
- **OpenSearchDown**: OpenSearch unavailable (>1 minute)

### Warning Alerts
- **HighResponseTime**: 95th percentile >2.0s (>2 minutes)
- **LowCacheHitRate**: Hit rate <60% (>3 minutes)
- **CircuitBreakerOpen**: Circuit breaker opened (>30 seconds)
- **HighMemoryUsage**: Memory usage >85% (>2 minutes)
- **HighCPUUsage**: CPU usage >80% (>5 minutes)
- **HighErrorRate**: Error rate >5% (>2 minutes)

### Performance Alerts
- **SlowContextRetrieval**: Context retrieval >1.5s (>2 minutes)
- **SlowLLMResponse**: LLM response >3.0s (>2 minutes)
- **CacheL1MemoryPressure**: L1 memory usage >90% (>1 minute)

## Configuration

### Prometheus Configuration
```yaml
# monitoring/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'ontology-chat-api'
    static_configs:
      - targets: ['host.docker.internal:8000']
    metrics_path: '/metrics'
```

### Grafana Datasource
```yaml
# monitoring/grafana/datasources/prometheus.yml
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
    isDefault: true
```

### AlertManager Configuration
```yaml
# monitoring/alertmanager/alertmanager.yml
route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'
```

## API Endpoints

### Metrics Endpoints
```bash
# Prometheus metrics
GET /metrics

# Health check
GET /metrics/health

# Cache metrics
GET /metrics/cache/prometheus

# Dashboard data
GET /metrics/dashboard

# Update quality score
POST /metrics/quality/update
```

### Health Check Response
```json
{
  "status": "healthy",
  "components": {
    "cache": {
      "healthy": true,
      "hit_rate": 0.85,
      "l1_connected": true,
      "l2_connected": true,
      "l3_connected": true
    },
    "llm": {"healthy": true},
    "databases": {
      "neo4j_healthy": true,
      "opensearch_healthy": true
    }
  },
  "uptime_seconds": 3600
}
```

## Performance Targets

### A-Grade Quality Maintenance
- **Quality Score**: ≥ 0.900 (A-grade threshold)
- **Response Time**: < 2.0 seconds (95th percentile)
- **Cache Hit Rate**: > 80% overall
- **Error Rate**: < 1% for critical operations
- **Availability**: > 99.9% uptime

### Cache Performance
- **L1 Hit Rate**: > 60% (memory cache)
- **L2 Hit Rate**: > 20% (Redis cache)
- **L3 Hit Rate**: > 10% (disk cache)
- **Cache Effectiveness**: > 0.8 score

### System Resources
- **Memory Usage**: < 85%
- **CPU Usage**: < 80%
- **Disk Usage**: < 85%

## Troubleshooting

### Common Issues

#### Prometheus Not Scraping Metrics
```bash
# Check if application is exposing metrics
curl http://localhost:8000/metrics

# Check Prometheus targets
# Go to http://localhost:9090/targets
```

#### Grafana Dashboards Not Loading
```bash
# Check Grafana logs
docker logs ontology_grafana

# Verify datasource connection
# Go to Grafana > Configuration > Data Sources > Test
```

#### Alerts Not Firing
```bash
# Check AlertManager logs
docker logs ontology_alertmanager

# Verify alert rules in Prometheus
# Go to http://localhost:9090/alerts
```

### Log Analysis
```bash
# View all monitoring logs
docker-compose -f docker-compose.monitoring.yml logs

# View specific service logs
docker logs ontology_prometheus
docker logs ontology_grafana
docker logs ontology_alertmanager
```

## Scaling and Production

### Production Deployment
1. **External Storage**: Configure external storage for Prometheus data
2. **Load Balancing**: Set up Grafana behind load balancer
3. **Backup Strategy**: Regular backup of Grafana dashboards and Prometheus data
4. **Security**: Configure authentication and SSL certificates

### Resource Requirements
- **Prometheus**: 2GB RAM, 2 CPU cores, 50GB storage
- **Grafana**: 1GB RAM, 1 CPU core, 10GB storage
- **AlertManager**: 512MB RAM, 1 CPU core, 5GB storage

### High Availability
For production environments:
- Deploy Prometheus in federation mode
- Use Grafana cluster setup
- Configure AlertManager clustering
- Implement external service discovery

## 🔍 Langfuse LLM Tracing Integration

### Overview
Langfuse provides comprehensive LLM observability and tracing capabilities integrated with our monitoring stack.

### Setup
- **URL**: http://localhost:3000
- **Environment Variables**: Already configured in `.env`
  - `LANGFUSE_SECRET_KEY`: sk-lf-778a499a-333f-47cf-8d1e-ed242f90b4e9
  - `LANGFUSE_PUBLIC_KEY`: pk-lf-fc1ffbd1-e92e-4648-90d7-7b9a5cac1c3c
  - `LANGFUSE_HOST`: http://192.168.0.10:3000

### LLM Monitoring Features
- **Trace Collection**: Automatic tracing of all LLM calls
- **Performance Analytics**: Response times, token usage, model comparisons
- **Cost Tracking**: Token-based cost analysis
- **Error Monitoring**: LLM failure pattern analysis
- **User Sessions**: Request tracking per user/session

### Available Dashboards
1. **LLM Observability & Performance**: Real-time LLM metrics
2. **Langfuse LLM Analytics**: Detailed analysis using Langfuse data
   - Total LLM calls (24h)
   - Average response times
   - Token usage trends
   - Success rates
   - Model performance comparison

### Key Metrics
```promql
# LLM Success Rate
rate(ontology_llm_requests_total{status="success"}[5m]) / rate(ontology_llm_requests_total[5m]) * 100

# Average LLM Response Time
avg(ontology_llm_response_time_seconds)

# Token Usage
sum(ontology_llm_tokens_total)
```

### Langfuse Analytics Queries
The Langfuse dashboard connects to the Langfuse PostgreSQL database:
```sql
-- Total LLM calls in last 24h
SELECT COUNT(*) FROM traces WHERE created_at >= NOW() - INTERVAL '24 hours'

-- Average response time
SELECT AVG(EXTRACT(EPOCH FROM (updated_at - created_at)))
FROM traces WHERE created_at >= NOW() - INTERVAL '24 hours'

-- Success rate
SELECT (COUNT(CASE WHEN level != 'ERROR' THEN 1 END) * 100.0 / COUNT(*)) as success_rate
FROM traces WHERE created_at >= NOW() - INTERVAL '24 hours'
```

## Integration with CI/CD

The monitoring setup integrates with the existing GitHub Actions pipeline:
- Health checks in deployment pipeline
- Performance regression detection
- Automated rollback on quality degradation
- **LLM performance tracking**: Langfuse metrics in deployment validation

## 🚀 Updated Service Ports

Due to port conflicts, services run on updated ports:
- **Prometheus**: http://localhost:9092 (changed from 9090)
- **Grafana**: http://localhost:3001
- **AlertManager**: http://localhost:9093
- **Langfuse**: http://localhost:3000
- **Node Exporter**: http://localhost:9100/metrics
- **Redis Exporter**: http://localhost:9121/metrics

This comprehensive monitoring solution ensures continuous visibility into both application performance and LLM behavior, enabling proactive maintenance of A-grade quality standards with full observability into AI/ML operations.