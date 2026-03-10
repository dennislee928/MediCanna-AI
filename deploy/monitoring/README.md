# Monitoring Assets

## Create Dashboard
```bash
gcloud monitoring dashboards create \
  --project "$PROJECT_ID" \
  --config-from-file deploy/monitoring/dashboard.json
```

## Create Alert Policy
```bash
gcloud alpha monitoring policies create \
  --project "$PROJECT_ID" \
  --policy-from-file deploy/monitoring/alert-policies.yaml
```

Update `notificationChannels` in `alert-policies.yaml` before applying in production.
