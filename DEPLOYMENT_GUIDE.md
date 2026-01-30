# Production Deployment Guide

**Version**: 1.0  
**Last Updated**: January 30, 2026

---

## Overview

This guide covers deploying the Procedural LTM system to production using Kubernetes. The system consists of multiple services that work together to provide a scalable, production-ready memory management platform.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Load Balancer (Ingress)                  │
│                   api.lltm.example.com                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Pods (3-10 replicas)                  │
│                   Auto-scaling enabled                       │
└─────┬──────────┬──────────┬──────────┬──────────────────────┘
      │          │          │          │
      ▼          ▼          ▼          ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│  Neo4j  │ │  Redis  │ │Postgres │ │ Celery  │
│ (Graph) │ │ (Cache) │ │(Vectors)│ │(Workers)│
└─────────┘ └─────────┘ └─────────┘ └─────────┘
```

---

## Prerequisites

### Required Tools
- `kubectl` v1.28+
- `docker` v24+
- `helm` v3+ (optional)
- Access to Kubernetes cluster

### Required Accounts
- GitHub account (for CI/CD)
- Container registry access (GitHub Container Registry)
- Kubernetes cluster (GKE, EKS, or AKS)
- Domain name for API

### Required Secrets
- JWT secret key
- Neo4j password
- PostgreSQL password
- Slack webhook (optional)

---

## Step 1: Prepare Kubernetes Cluster

### Create Cluster (GKE Example)
```bash
# Create GKE cluster
gcloud container clusters create lltm-production \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type n1-standard-4 \
  --enable-autoscaling \
  --min-nodes 3 \
  --max-nodes 10

# Get credentials
gcloud container clusters get-credentials lltm-production \
  --zone us-central1-a
```

### Install Ingress Controller
```bash
# Install NGINX Ingress
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml

# Wait for external IP
kubectl get svc -n ingress-nginx
```

### Install Cert Manager (for TLS)
```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create Let's Encrypt issuer
kubectl apply -f k8s/cert-issuer.yaml
```

---

## Step 2: Configure Secrets

### Generate Secrets
```bash
# Generate JWT secret
JWT_SECRET=$(openssl rand -base64 32)

# Generate database passwords
NEO4J_PASSWORD=$(openssl rand -base64 16)
POSTGRES_PASSWORD=$(openssl rand -base64 16)

# Create Kubernetes secret
kubectl create secret generic lltm-secrets \
  --from-literal=JWT_SECRET_KEY=$JWT_SECRET \
  --from-literal=NEO4J_PASSWORD=$NEO4J_PASSWORD \
  --from-literal=POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
  -n lltm-production
```

### Update ConfigMap
```bash
# Edit k8s/deployment.yaml
# Update domain name in Ingress section
# Update any environment-specific values

kubectl apply -f k8s/deployment.yaml
```

---

## Step 3: Deploy Services

### Deploy All Services
```bash
# Apply all Kubernetes manifests
kubectl apply -f k8s/deployment.yaml

# Verify deployments
kubectl get pods -n lltm-production
kubectl get svc -n lltm-production
kubectl get ingress -n lltm-production
```

### Check Pod Status
```bash
# Watch pod startup
kubectl get pods -n lltm-production -w

# Check logs
kubectl logs -f deployment/lltm-api -n lltm-production
kubectl logs -f deployment/lltm-celery-worker -n lltm-production
```

### Verify Services
```bash
# Check API health
kubectl port-forward svc/lltm-api 8000:8000 -n lltm-production
curl http://localhost:8000/health

# Check Neo4j
kubectl port-forward svc/neo4j 7474:7474 -n lltm-production
# Open http://localhost:7474 in browser

# Check Redis
kubectl port-forward svc/redis 6379:6379 -n lltm-production
redis-cli -h localhost ping
```

---

## Step 4: Configure DNS

### Point Domain to Load Balancer
```bash
# Get external IP
EXTERNAL_IP=$(kubectl get ingress lltm-ingress -n lltm-production -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "Point api.lltm.example.com to $EXTERNAL_IP"
```

### Update DNS Records
```
Type: A
Name: api.lltm.example.com
Value: <EXTERNAL_IP>
TTL: 300
```

### Verify DNS
```bash
# Wait for DNS propagation
dig api.lltm.example.com

# Test HTTPS
curl https://api.lltm.example.com/health
```

---

## Step 5: Set Up CI/CD

### Configure GitHub Secrets
```bash
# In GitHub repository settings, add secrets:
KUBE_CONFIG_STAGING     # Base64 encoded kubeconfig for staging
KUBE_CONFIG_PRODUCTION  # Base64 encoded kubeconfig for production
SLACK_WEBHOOK          # Slack webhook URL for notifications

# Get kubeconfig
kubectl config view --raw | base64
```

### Enable GitHub Actions
```bash
# Push code to main branch
git add .
git commit -m "Add production deployment"
git push origin main

# GitHub Actions will automatically:
# 1. Run tests
# 2. Build Docker image
# 3. Deploy to staging
# 4. Deploy to production (after approval)
```

### Monitor Deployment
```bash
# Watch GitHub Actions
# https://github.com/YOUR_ORG/LLTM/actions

# Check deployment status
kubectl rollout status deployment/lltm-api -n lltm-production
```

---

## Step 6: Configure Monitoring

### Deploy Prometheus + Grafana
```bash
# Install Prometheus Operator
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace

# Access Grafana
kubectl port-forward svc/prometheus-grafana 3000:80 -n monitoring
# Open http://localhost:3000 (admin/prom-operator)

# Import LLTM dashboard
# Upload monitoring/grafana/lltm_dashboard.json
```

### Configure Alerts
```bash
# Apply alerting rules
kubectl apply -f monitoring/prometheus/alerts.yml

# Configure alert routing
kubectl edit alertmanager prometheus-kube-prometheus-alertmanager -n monitoring
```

---

## Step 7: Verify Production Deployment

### Run Smoke Tests
```bash
# Health check
curl https://api.lltm.example.com/health

# Register user
curl -X POST https://api.lltm.example.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "full_name": "Test User"
  }'

# Login
curl -X POST https://api.lltm.example.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }'

# Get token and test API
TOKEN="<access_token_from_login>"
curl https://api.lltm.example.com/api/v1/memory/user_1 \
  -H "Authorization: Bearer $TOKEN"
```

### Run Load Tests
```bash
# Install Locust
pip install locust

# Run load test
locust -f tests/load/locustfile.py \
  --host=https://api.lltm.example.com \
  --users 100 --spawn-rate 10 --run-time 5m
```

---

## Scaling

### Manual Scaling
```bash
# Scale API pods
kubectl scale deployment lltm-api --replicas=5 -n lltm-production

# Scale Celery workers
kubectl scale deployment lltm-celery-worker --replicas=4 -n lltm-production
```

### Auto-scaling
```bash
# HPA is already configured in deployment.yaml
# Scales based on CPU (70%) and Memory (80%)
# Min: 3 replicas, Max: 10 replicas

# Check HPA status
kubectl get hpa -n lltm-production
```

### Database Scaling
```bash
# Neo4j: Increase resources in StatefulSet
kubectl edit statefulset neo4j -n lltm-production

# PostgreSQL: Increase resources
kubectl edit statefulset postgres -n lltm-production

# Redis: Consider Redis Cluster for high availability
```

---

## Backup & Recovery

### Database Backups
```bash
# Neo4j backup
kubectl exec -it neo4j-0 -n lltm-production -- \
  neo4j-admin database backup neo4j --to-path=/backups

# PostgreSQL backup
kubectl exec -it postgres-0 -n lltm-production -- \
  pg_dump -U lltm lltm_vectors > backup.sql

# Copy backups to local
kubectl cp lltm-production/neo4j-0:/backups ./neo4j-backup
kubectl cp lltm-production/postgres-0:/backup.sql ./postgres-backup.sql
```

### Automated Backups
```bash
# Set up CronJob for daily backups
kubectl apply -f k8s/backup-cronjob.yaml

# Verify backup schedule
kubectl get cronjob -n lltm-production
```

### Disaster Recovery
```bash
# Restore Neo4j
kubectl exec -it neo4j-0 -n lltm-production -- \
  neo4j-admin database restore neo4j --from-path=/backups

# Restore PostgreSQL
kubectl exec -it postgres-0 -n lltm-production -- \
  psql -U lltm lltm_vectors < backup.sql
```

---

## Troubleshooting

### Pod Not Starting
```bash
# Check pod status
kubectl describe pod <pod-name> -n lltm-production

# Check logs
kubectl logs <pod-name> -n lltm-production

# Common issues:
# - Image pull errors: Check registry credentials
# - CrashLoopBackOff: Check application logs
# - Pending: Check resource availability
```

### High Memory Usage
```bash
# Check resource usage
kubectl top pods -n lltm-production

# Increase memory limits
kubectl edit deployment lltm-api -n lltm-production

# Check for memory leaks
kubectl logs deployment/lltm-api -n lltm-production | grep "memory"
```

### Slow API Responses
```bash
# Check Prometheus metrics
# Open Grafana dashboard

# Check database performance
kubectl exec -it neo4j-0 -n lltm-production -- \
  cypher-shell "CALL dbms.listQueries()"

# Check Redis cache hit rate
kubectl exec -it redis-0 -n lltm-production -- \
  redis-cli INFO stats
```

### Database Connection Issues
```bash
# Test Neo4j connection
kubectl exec -it neo4j-0 -n lltm-production -- \
  cypher-shell -u neo4j -p <password>

# Test PostgreSQL connection
kubectl exec -it postgres-0 -n lltm-production -- \
  psql -U lltm -d lltm_vectors

# Check service endpoints
kubectl get endpoints -n lltm-production
```

---

## Rollback Procedure

### Automatic Rollback
```bash
# GitHub Actions automatically rolls back on failure
# Check .github/workflows/deploy.yml
```

### Manual Rollback
```bash
# Rollback to previous version
kubectl rollout undo deployment/lltm-api -n lltm-production

# Rollback to specific revision
kubectl rollout history deployment/lltm-api -n lltm-production
kubectl rollout undo deployment/lltm-api --to-revision=2 -n lltm-production

# Verify rollback
kubectl rollout status deployment/lltm-api -n lltm-production
```

---

## Maintenance

### Update Application
```bash
# Update via CI/CD (recommended)
git push origin main

# Manual update
kubectl set image deployment/lltm-api \
  lltm-api=ghcr.io/your-org/lltm-api:v1.2.0 \
  -n lltm-production
```

### Update Dependencies
```bash
# Update base images in Dockerfile
# Update requirements.txt
# Run CI/CD pipeline
```

### Rotate Secrets
```bash
# Generate new secrets
NEW_JWT_SECRET=$(openssl rand -base64 32)

# Update secret
kubectl create secret generic lltm-secrets \
  --from-literal=JWT_SECRET_KEY=$NEW_JWT_SECRET \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart pods to pick up new secret
kubectl rollout restart deployment/lltm-api -n lltm-production
```

---

## Security Checklist

- [ ] TLS/HTTPS enabled
- [ ] Secrets stored in Kubernetes Secrets
- [ ] Network policies configured
- [ ] RBAC enabled
- [ ] Pod security policies applied
- [ ] Regular security scans (Trivy)
- [ ] Rate limiting configured
- [ ] Authentication required on all endpoints
- [ ] Database passwords rotated regularly
- [ ] Backups encrypted

---

## Performance Tuning

### API Optimization
```python
# Increase worker processes
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
```

### Database Optimization
```cypher
// Neo4j: Create additional indexes
CREATE INDEX atom_confidence_index FOR (a:Atom) ON (a.confidence)
CREATE INDEX atom_last_accessed_index FOR (a:Atom) ON (a.last_accessed)
```

### Cache Optimization
```python
# Increase cache TTLs for stable data
TTL_USER_ATOMS = 600  # 10 minutes
TTL_STABILITY_SCORE = 1200  # 20 minutes
```

---

## Cost Optimization

### Resource Requests
```yaml
# Right-size resource requests
resources:
  requests:
    memory: "256Mi"  # Start small
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

### Auto-scaling
```bash
# Use cluster autoscaler
# Scale down during off-hours
# Use spot instances for non-critical workloads
```

---

## Support

### Monitoring
- Grafana: https://grafana.lltm.example.com
- Prometheus: https://prometheus.lltm.example.com

### Logs
```bash
# View logs
kubectl logs -f deployment/lltm-api -n lltm-production

# Aggregate logs
# Use ELK stack or Datadog
```

### Alerts
- Slack: #lltm-alerts
- PagerDuty: lltm-oncall
- Email: ops@lltm.example.com

---

## Conclusion

The Procedural LTM system is now deployed to production with:
- High availability (3-10 API replicas)
- Auto-scaling enabled
- Comprehensive monitoring
- Automated CI/CD
- Disaster recovery procedures

For questions or issues, refer to the troubleshooting section or contact the operations team.
