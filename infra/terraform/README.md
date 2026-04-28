# FlowSight infrastructure

Terraform module that provisions everything FlowSight needs on GCP:

- Artifact Registry (Docker images)
- Cloud Run (FastAPI backend)
- Pub/Sub (event ingestion)
- Firestore (live state)
- BigQuery (analytics: events + decisions)
- Secret Manager (Gemini API key, optional)
- Firebase Hosting site (PWA frontend)

## One-time bootstrap

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

## Apply

```bash
cd infra/terraform
terraform init
terraform apply \
  -var="project_id=$(gcloud config get-value project)" \
  -var="region=asia-south1" \
  -var="gemini_api_key=$GEMINI_API_KEY"
```

The first apply takes 5–10 min (enabling APIs is the slow step).

## Push the backend image

After Cloud Build runs once (via `cloudbuild.yaml`) the backend image
will exist at:

```
asia-south1-docker.pkg.dev/$PROJECT_ID/flowsight/flowsight-api:latest
```

Re-run `terraform apply` with `image_tag=<sha>` to pin a deploy.

## Deploy the frontend

```bash
cd ../../frontend
npm run build
firebase deploy --only hosting --project $PROJECT_ID
```

(set the hosting target to the site_id output by Terraform)

## Costs

All resources fit within GCP free tier for demo-level usage:

| Resource         | Free tier                       |
|------------------|----------------------------------|
| Cloud Run        | 2M requests/month, 360k GB-sec  |
| Pub/Sub          | 10 GB/month                      |
| Firestore        | 50K reads/day, 1 GiB             |
| BigQuery         | 1 TB queries/month, 10 GB store  |
| Artifact Registry| 0.5 GB                           |
| Secret Manager   | 6 secret versions                |

Set a billing alert at $1 just to be safe:
`gcloud billing budgets create ...`
