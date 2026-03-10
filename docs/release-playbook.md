# MediCanna Release Playbook

## Versioning and Release Notes
- Tag each production release as `vYYYY.MM.DD.N` or semver (`v1.2.3`).
- The tag value is used as Cloud Run image tag (`TAG`) for all services.
- Add release notes under:
  - Scope of change
  - Risk assessment
  - Validation results (`scripts/verify-api.sh`, CI links)
  - Rollback target tag

## Deployment
- Run the GitHub workflow `Release Cloud Run` or execute:
  - `PROJECT_ID=<project> REGION=<region> TAG=<tag> bash deploy/cloudrun/deploy.sh`
- Confirm all services are healthy:
  - `GET /healthz`
  - `GET /readyz`

## Rollback
1. Identify previous stable tag, e.g. `v1.3.2`.
2. Re-run deployment using that tag:
   - `PROJECT_ID=<project> REGION=<region> TAG=v1.3.2 bash deploy/cloudrun/deploy.sh`
3. Validate:
   - Frontend smoke test
   - Gateway `POST /api/v1/recommend`
   - Cloud Run metrics return to baseline

## Operational Checks
- Alert on p95 latency regression, 5xx surge, and readiness failures.
- Correlate incidents using `request_id` in gateway + ML structured logs.
