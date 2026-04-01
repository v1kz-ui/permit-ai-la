# Deployment Runbook - PermitAI LA

## Pre-Deployment Checklist

- [ ] All tests pass on the branch (`test.yml` workflow is green)
- [ ] Security scan has no critical findings (`security-scan.yml`)
- [ ] Database migrations reviewed and tested against a staging copy
- [ ] Changes have been deployed to staging and validated
- [ ] Load testing completed if the change affects performance-sensitive paths
- [ ] Rollback plan confirmed (previous task definition ARN noted)
- [ ] Team notified in Slack `#permitai-deploys` channel
- [ ] On-call engineer available during deploy window

## Blue/Green Deployment Steps

### 1. Trigger Production Deployment

Navigate to GitHub Actions and trigger the `deploy-production.yml` workflow:

1. Go to **Actions** > **Deploy to Production**
2. Click **Run workflow**
3. Select environment: `production`
4. Click **Run workflow**

The workflow will:
- Build and push the Docker image to ECR
- Run database migrations (requires environment approval)
- Register a new ECS task definition with the new image
- Update the ECS service to use the new task definition
- Wait for service stability
- Run smoke tests
- Auto-rollback on failure

### 2. Monitor Deployment Progress

Monitor the following during deployment:

- **GitHub Actions**: Watch the workflow run for each step
- **ECS Console**: Observe task replacement (old tasks draining, new tasks starting)
- **CloudWatch Dashboard**: `permitai-production` - watch for error spikes
- **Health endpoints**:
  ```bash
  curl https://api.permitai.la/api/v1/monitoring/health/ready
  curl https://api.permitai.la/api/v1/monitoring/health/live
  curl https://api.permitai.la/api/v1/monitoring/health/detailed
  ```

### 3. Verify Deployment

After the workflow completes successfully:

1. Confirm new tasks are running: check ECS service "Running count"
2. Confirm old tasks are drained: check ECS service "Desired count" matches "Running count"
3. Check application version in health response
4. Spot-check key user flows in the dashboard

## Database Migration Procedure

### Before Migrating

1. Create a database backup:
   ```bash
   # Generate backup command
   python -c "from app.core.backup import BackupService; print(BackupService().create_backup())"
   ```
2. Review the migration SQL:
   ```bash
   cd backend
   alembic upgrade head --sql
   ```
3. Test migration against staging database first
4. For destructive migrations (dropping columns/tables), ensure the previous application version does not depend on the dropped schema

### Running Migrations

Migrations run automatically as part of the deploy workflow. For manual execution:

```bash
cd backend
DATABASE_URL_SYNC=<production_url> alembic upgrade head
```

### Migration Rollback

```bash
cd backend
# Check current revision
alembic current

# Downgrade one revision
DATABASE_URL_SYNC=<production_url> alembic downgrade -1

# Or downgrade to a specific revision
DATABASE_URL_SYNC=<production_url> alembic downgrade <revision_id>
```

## Rollback Procedure

### Automatic Rollback

The deploy workflow automatically rolls back if smoke tests fail. It reverts the ECS service to the previous task definition.

### Manual Rollback

If issues are detected after deployment:

1. **Identify the previous task definition:**
   ```bash
   aws ecs describe-services \
     --cluster permitai-production \
     --services permitai-api \
     --query 'services[0].deployments' \
     --output table
   ```

2. **Revert to the previous task definition:**
   ```bash
   aws ecs update-service \
     --cluster permitai-production \
     --service permitai-api \
     --task-definition <previous-task-definition-arn> \
     --force-new-deployment
   ```

3. **Wait for stability:**
   ```bash
   aws ecs wait services-stable \
     --cluster permitai-production \
     --services permitai-api
   ```

4. **If database migrations need reverting**, follow the migration rollback procedure above

5. **Notify the team** in `#permitai-deploys` with details

## Smoke Test Checklist

These are run automatically by the deploy workflow but can be run manually:

- [ ] `GET /api/v1/health` returns `200` with `status: healthy`
- [ ] `GET /api/v1/monitoring/health/ready` returns `200` with `ready: true`
- [ ] `GET /api/v1/monitoring/health/live` returns `200` with `alive: true`
- [ ] `GET /api/v1/projects` returns `200` (authenticated)
- [ ] `GET /api/v1/clearances` returns `200`
- [ ] Dashboard loads and displays data at `https://app.permitai.la`

## Post-Deployment Monitoring

After a successful deployment, monitor for 30 minutes:

1. **Error rate**: CloudWatch alarm should not trigger (threshold: >5%)
2. **Latency**: P99 should remain below 3 seconds
3. **CPU/Memory**: ECS task metrics should be within normal range
4. **Logs**: Check for new error patterns in CloudWatch Logs
   ```bash
   aws logs filter-log-events \
     --log-group-name /permitai/production/api \
     --filter-pattern "ERROR" \
     --start-time $(date -d '30 minutes ago' +%s000)
   ```
5. **Cache**: Verify cache is warming correctly via `/api/v1/monitoring/health/detailed`
6. **Data pipeline**: Confirm Airflow DAGs are still running on schedule

If any anomalies are detected within the monitoring window, follow the rollback procedure.
