---
type: claude-context
directory: terraform
purpose: Infrastructure as Code for GCP deployment
parent: ../CLAUDE.md
sibling_readme: null
children: []
---

# Claude Code Context: terraform

Terraform configuration for GCP infrastructure.

## Files

- `main.tf` - GCP resources (Cloud Run, GCS, Pub/Sub)
- `iam.tf` - Service accounts and permissions
- `variables.tf` - Configuration variables
- `outputs.tf` - Output values

## Deployment

```bash
cd terraform
terraform init
terraform plan -var="project_id=PROJECT_ID" -var="region=REGION"
terraform apply
```

## Related

- **Parent**: [media-intelligence](../CLAUDE.md)
