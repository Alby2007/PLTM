# Deployment Guide

Complete guide for deploying the Procedural LTM system to production.

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Docker (optional, for containerized deployment)
- PostgreSQL or SQLite

### Local Setup (5 minutes)

```bash
# Clone repository
git clone https://github.com/Alby2007/LLTM.git
cd LLTM

# Install dependencies
pip install -r requirements.txt

# Run tests to verify
pytest tests/

# Start the system
python -m src.pipeline.memory_pipeline
```

See `../../REPRODUCE.md` for detailed reproduction steps.

---

## 🐳 Docker Deployment

### Using Docker Compose (Recommended for Local)

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Docker Compose Configuration

```yaml
version: '3.8'

services:
  lltm-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/lltm
      - LOG_LEVEL=INFO
    depends_on:
      - db
      - redis
    
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=lltm
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  postgres_data:
  grafana_data:
```

---

## ☸️ Kubernetes Deployment (Production)

### Prerequisites
- Kubernetes cluster (GKE, EKS, AKS, or local minikube)
- kubectl configured
- Helm 3+ (optional, for easier management)

### Deploy to Kubernetes

```bash
# Create namespace
kubectl create namespace lltm

# Apply configurations
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n lltm
kubectl get services -n lltm

# View logs
kubectl logs -f deployment/lltm-api -n lltm
```

### Kubernetes Resources

**Deployment** (`k8s/deployment.yaml`):
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lltm-api
  namespace: lltm
spec:
  replicas: 3
  selector:
    matchLabels:
      app: lltm-api
  template:
    metadata:
      labels:
        app: lltm-api
    spec:
      containers:
      - name: lltm-api
        image: your-registry/lltm:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: lltm-secrets
              key: database-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

**Service** (`k8s/service.yaml`):
```yaml
apiVersion: v1
kind: Service
metadata:
  name: lltm-api
  namespace: lltm
spec:
  type: LoadBalancer
  selector:
    app: lltm-api
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
```

**HorizontalPodAutoscaler** (`k8s/hpa.yaml`):
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: lltm-api-hpa
  namespace: lltm
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: lltm-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## 📊 Monitoring & Observability

### Prometheus Metrics

The system exposes Prometheus metrics at `/metrics`:

**Key Metrics:**
- `judge_evaluations_total` - Total evaluations by judge
- `judge_accuracy` - Historical accuracy per judge
- `judge_latency_seconds` - Evaluation latency
- `judge_confidence` - Confidence score distribution
- `conflict_detection_rate` - Conflict detection rate

### Grafana Dashboards

Import pre-built dashboards from `monitoring/grafana/`:
- **System Overview** - High-level metrics
- **Judge Performance** - Per-judge analytics
- **Conflict Resolution** - Conflict detection stats
- **Performance** - Latency and throughput

### Accessing Monitoring

```bash
# Prometheus (metrics)
http://localhost:9090

# Grafana (dashboards)
http://localhost:3000
# Default credentials: admin/admin
```

---

## 🔒 Security & Configuration

### Environment Variables

Create `.env` file:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/lltm

# Redis (optional, for caching)
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# API Keys (if using external LLM)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Security
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,yourdomain.com

# Performance
MAX_WORKERS=4
CACHE_TTL=3600
```

### Secrets Management

**Kubernetes Secrets:**
```bash
# Create secret
kubectl create secret generic lltm-secrets \
  --from-literal=database-url='postgresql://...' \
  --from-literal=openai-api-key='sk-...' \
  -n lltm

# Verify
kubectl get secrets -n lltm
```

---

## 🔧 Production Checklist

### Before Deployment

- [ ] Run full test suite: `pytest tests/`
- [ ] Run benchmarks: `python run_300_comprehensive_benchmark.py`
- [ ] Configure environment variables
- [ ] Set up database (PostgreSQL recommended for production)
- [ ] Configure monitoring (Prometheus + Grafana)
- [ ] Set up logging aggregation (ELK, Datadog, etc.)
- [ ] Configure auto-scaling policies
- [ ] Set up backup strategy
- [ ] Review security settings
- [ ] Load test the system

### After Deployment

- [ ] Verify health endpoints: `/health`, `/ready`
- [ ] Check Prometheus metrics
- [ ] Review Grafana dashboards
- [ ] Test conflict detection with sample data
- [ ] Monitor error rates
- [ ] Set up alerts for critical metrics
- [ ] Document runbook for common issues

---

## 📈 Scaling Recommendations

### Small Scale (< 1000 users)
- **Deployment**: Single instance or Docker Compose
- **Database**: SQLite or small PostgreSQL
- **Resources**: 1 CPU, 512MB RAM
- **Cost**: ~$10-20/month

### Medium Scale (1000-10,000 users)
- **Deployment**: Kubernetes with 3-5 replicas
- **Database**: PostgreSQL with read replicas
- **Resources**: 2-4 CPUs, 2-4GB RAM per pod
- **Caching**: Redis for frequently accessed data
- **Cost**: ~$100-300/month

### Large Scale (10,000+ users)
- **Deployment**: Kubernetes with auto-scaling (10-50 replicas)
- **Database**: PostgreSQL cluster with sharding
- **Resources**: 4-8 CPUs, 8-16GB RAM per pod
- **Caching**: Redis cluster
- **CDN**: For static assets
- **Cost**: ~$500-2000/month

---

## 🐛 Troubleshooting

### Common Issues

**1. Database Connection Errors**
```bash
# Check database is running
docker-compose ps db

# Test connection
psql $DATABASE_URL

# Check logs
docker-compose logs db
```

**2. High Memory Usage**
```bash
# Check pod memory
kubectl top pods -n lltm

# Increase memory limits in deployment.yaml
resources:
  limits:
    memory: "1Gi"  # Increase from 512Mi
```

**3. Slow Performance**
```bash
# Check Prometheus metrics
# Look for high latency in judge_latency_seconds

# Enable caching
CACHE_TTL=3600

# Scale up replicas
kubectl scale deployment lltm-api --replicas=5 -n lltm
```

**4. Failed Health Checks**
```bash
# Check health endpoint
curl http://localhost:8000/health

# View logs
kubectl logs -f deployment/lltm-api -n lltm

# Check database connectivity
```

---

## 📚 Additional Resources

- **Architecture**: `../architecture/TECHNICAL_DESIGN.md`
- **API Documentation**: `../api/REFERENCE.md`
- **Monitoring Setup**: `../../monitoring/README.md`
- **Kubernetes Configs**: `../../k8s/README.md`

---

## 🆘 Support

For deployment issues:
1. Check logs: `kubectl logs` or `docker-compose logs`
2. Review metrics in Grafana
3. Consult troubleshooting section above
4. Open GitHub issue with logs and configuration

---

## 🎯 Production Best Practices

1. **Always use PostgreSQL** in production (not SQLite)
2. **Enable monitoring** from day one
3. **Set up alerts** for critical metrics
4. **Use auto-scaling** to handle traffic spikes
5. **Implement circuit breakers** for external dependencies
6. **Regular backups** of database
7. **Blue-green deployments** for zero-downtime updates
8. **Load testing** before major releases

---

**Status**: Production-ready ✅  
**Last Updated**: January 31, 2026
