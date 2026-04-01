# Incident Response Runbook - PermitAI LA

## Severity Levels

| Level | Description | Response Time | Examples |
|-------|-------------|---------------|----------|
| P1 - Critical | Service is down or data loss is occurring | 15 minutes | Full API outage, database corruption, security breach |
| P2 - High | Major feature is broken, significant user impact | 1 hour | Authentication failures, pipeline completely stalled, 5xx rate >10% |
| P3 - Medium | Degraded performance or minor feature broken | 4 hours | Elevated latency, non-critical endpoint errors, cache failures |
| P4 - Low | Cosmetic or minor issue, minimal user impact | Next business day | Logging gaps, dashboard display issues, non-critical alerts |

## Escalation Path

1. **On-call engineer** - First responder, triages and begins remediation
2. **Engineering lead** - Escalated if not resolved within response time SLA
3. **Platform lead** - Escalated for infrastructure issues or P1 incidents
4. **CTO / VP Engineering** - Escalated for extended P1 outages (>1 hour)

Contact information is maintained in the team PagerDuty configuration.

---

## Common Incidents

### 1. Database Connection Pool Exhaustion

**Symptoms:**
- API responses return 500 errors with "connection pool exhausted" or timeout messages
- CloudWatch alarm: high error rate triggered
- Monitoring endpoint `/api/v1/monitoring/health/detailed` shows `checked_out` near pool max
- Application logs show `QueuePool limit` or `TimeoutError` from SQLAlchemy

**Diagnosis Steps:**
1. Check pool stats: `GET /api/v1/monitoring/health/detailed` - look at `database_pool`
2. Check for long-running queries:
   ```sql
   SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
   FROM pg_stat_activity
   WHERE state != 'idle'
   ORDER BY duration DESC;
   ```
3. Check for idle-in-transaction connections:
   ```sql
   SELECT count(*) FROM pg_stat_activity WHERE state = 'idle in transaction';
   ```
4. Review recent deployments for new queries without proper session management

**Remediation:**
1. Terminate long-running queries if safe:
   ```sql
   SELECT pg_terminate_backend(pid) FROM pg_stat_activity
   WHERE duration > interval '5 minutes' AND state != 'idle';
   ```
2. If pool is fully exhausted, restart the ECS service:
   ```bash
   aws ecs update-service --cluster permitai-production --service permitai-api --force-new-deployment
   ```
3. Temporarily increase pool size if needed (update environment variable `DATABASE_POOL_SIZE`)

**Prevention:**
- Ensure all database sessions use `async with` context managers
- Set query timeouts at the database level
- Monitor pool utilization and set alarms at 80% capacity

---

### 2. Redis Out of Memory (OOM)

**Symptoms:**
- Cache operations fail with OOM errors
- API latency increases (cache misses falling through to DB)
- CloudWatch alarm for ElastiCache memory utilization
- `/api/v1/monitoring/health/detailed` shows high `used_memory_mb`

**Diagnosis Steps:**
1. Check Redis memory: `GET /api/v1/monitoring/health/detailed` - look at `redis`
2. Connect to Redis and check memory:
   ```bash
   redis-cli -h <host> INFO memory
   ```
3. Check for large keys:
   ```bash
   redis-cli -h <host> --bigkeys
   ```
4. Check eviction policy: `redis-cli CONFIG GET maxmemory-policy`

**Remediation:**
1. Flush non-critical cache keys:
   ```bash
   redis-cli -h <host> EVAL "for _,k in ipairs(redis.call('keys','cache:*')) do redis.call('del',k) end" 0
   ```
2. If a specific pattern is consuming excessive memory, invalidate it through the cache service
3. Scale the ElastiCache node if memory is persistently insufficient

**Prevention:**
- Set appropriate TTLs on all cache keys
- Configure `maxmemory-policy allkeys-lru`
- Monitor memory usage and set alarms at 75% capacity
- Review cache key patterns periodically for unbounded growth

---

### 3. API 5xx Spike

**Symptoms:**
- CloudWatch alarm: high error rate (>5%)
- Users reporting failures
- Monitoring metrics show elevated error counts

**Diagnosis Steps:**
1. Check error breakdown: `GET /api/v1/monitoring/metrics` - look at error types and paths
2. Check application logs:
   ```bash
   aws logs filter-log-events \
     --log-group-name /permitai/production/api \
     --filter-pattern "ERROR" \
     --start-time $(date -d '30 minutes ago' +%s000)
   ```
3. Check if errors are isolated to specific endpoints or widespread
4. Check recent deployments: was there a deploy in the last hour?
5. Check downstream dependencies (DB, Redis, external APIs)

**Remediation:**
1. If caused by a recent deploy, initiate rollback (see deployment runbook)
2. If caused by a downstream dependency, follow the specific runbook for that dependency
3. If caused by a traffic spike, check WAF rate limiting and consider scaling ECS tasks:
   ```bash
   aws ecs update-service --cluster permitai-production --service permitai-api --desired-count 4
   ```
4. If caused by a specific endpoint, consider disabling it via feature flag if available

**Prevention:**
- Comprehensive integration tests before deployment
- Canary deployments for high-risk changes
- Circuit breakers for external dependencies
- Load testing before major releases

---

### 4. Pipeline Data Staleness

**Symptoms:**
- Parcel or clearance data is outdated (not reflecting recent LA city updates)
- Airflow DAGs show failures or long-running tasks
- Users report stale information in the dashboard

**Diagnosis Steps:**
1. Check Airflow UI for DAG run status and failures
2. Check the most recent successful data sync:
   ```sql
   SELECT MAX(updated_at) FROM parcels;
   SELECT MAX(updated_at) FROM clearances;
   ```
3. Check Airflow logs in CloudWatch: `/permitai/production/airflow`
4. Verify Socrata API availability:
   ```bash
   curl -I "https://data.lacity.org/resource/hbkd-qubn.json?$limit=1"
   ```

**Remediation:**
1. If Airflow DAG failed, check logs and retry:
   ```bash
   # Via Airflow CLI or UI
   airflow dags trigger socrata_sync
   ```
2. If Socrata API is down, wait and monitor; the DAG will retry on its next schedule
3. If data is corrupted, restore from the most recent backup (see backup procedures)

**Prevention:**
- Set up alerts for DAG failures and data freshness
- Implement dead-letter queues for failed records
- Monitor Socrata API status page for planned maintenance

---

## Post-Incident Review Template

Complete this template within 48 hours of any P1 or P2 incident.

```
## Post-Incident Review

**Date:** YYYY-MM-DD
**Severity:** P1/P2/P3/P4
**Duration:** Start time - End time (total minutes)
**Impact:** Description of user impact and scope

### Timeline
- HH:MM - Incident detected (how?)
- HH:MM - First responder engaged
- HH:MM - Root cause identified
- HH:MM - Remediation applied
- HH:MM - Service restored
- HH:MM - All-clear declared

### Root Cause
[Detailed description of the root cause]

### What Went Well
- [Item 1]
- [Item 2]

### What Could Be Improved
- [Item 1]
- [Item 2]

### Action Items
| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| [Action 1] | [Name] | YYYY-MM-DD | Open |
| [Action 2] | [Name] | YYYY-MM-DD | Open |

### Lessons Learned
[Key takeaways for the team]
```
