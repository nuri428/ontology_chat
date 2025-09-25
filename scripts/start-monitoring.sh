#!/bin/bash

# Ontology Chat Monitoring Startup Script
# This script starts the monitoring stack (Prometheus, Grafana, AlertManager)

set -e

echo "🚀 Starting Ontology Chat Monitoring Stack..."

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is required but not installed. Please install docker-compose first."
    exit 1
fi

# Check if monitoring configuration exists
if [ ! -f "docker-compose.monitoring.yml" ]; then
    echo "❌ Monitoring configuration not found. Please ensure docker-compose.monitoring.yml exists."
    exit 1
fi

# Create necessary directories
mkdir -p monitoring/prometheus/rules
mkdir -p monitoring/grafana/dashboards
mkdir -p monitoring/grafana/datasources
mkdir -p monitoring/alertmanager

# Start monitoring services
echo "📊 Starting Prometheus, Grafana, and AlertManager..."
docker-compose -f docker-compose.monitoring.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check service health
echo "🔍 Checking service health..."

# Check Prometheus
if curl -s http://localhost:9092/-/ready > /dev/null 2>&1; then
    echo "✅ Prometheus is ready at http://localhost:9092"
else
    echo "⚠️  Prometheus may not be ready yet. Check logs with: docker logs ontology_prometheus"
fi

# Check Grafana
if curl -s http://localhost:3001/api/health > /dev/null 2>&1; then
    echo "✅ Grafana is ready at http://localhost:3001"
    echo "   Default credentials: admin / ontology_admin_2024"
else
    echo "⚠️  Grafana may not be ready yet. Check logs with: docker logs ontology_grafana"
fi

# Check AlertManager
if curl -s http://localhost:9093/-/ready > /dev/null 2>&1; then
    echo "✅ AlertManager is ready at http://localhost:9093"
else
    echo "⚠️  AlertManager may not be ready yet. Check logs with: docker logs ontology_alertmanager"
fi

# Check Langfuse
if curl -s http://localhost:3000/api/public/health > /dev/null 2>&1; then
    echo "✅ Langfuse is ready at http://localhost:3000"
else
    echo "⚠️  Langfuse may not be ready yet. Check logs with: docker logs ontology_langfuse"
fi

echo ""
echo "🎯 Monitoring Stack Summary:"
echo "   Prometheus:    http://localhost:9092"
echo "   Grafana:       http://localhost:3001 (admin/ontology_admin_2024)"
echo "   AlertManager:  http://localhost:9093"
echo "   Langfuse:      http://localhost:3000"
echo ""
echo "📈 Available Dashboards:"
echo "   1. LLM Observability & Performance"
echo "   2. Langfuse LLM Analytics"
echo "   3. Ontology Chat - System Overview"
echo "   4. Cache Performance"
echo ""
echo "📊 To view logs:"
echo "   docker logs ontology_prometheus"
echo "   docker logs ontology_grafana"
echo "   docker logs ontology_alertmanager"
echo ""
echo "🛑 To stop monitoring:"
echo "   docker-compose -f docker-compose.monitoring.yml down"
echo ""
echo "✨ Monitoring setup complete!"