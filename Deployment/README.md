# EKS Deployment

This project uses two deployment files because an EKS cluster is created by AWS tooling, while application workloads are created by Kubernetes after the cluster exists.

## 1. Edit Placeholders

Update these values before applying:

- `Deployment/eks-cluster.yaml`
  - `metadata.region`
  - node size/counts if needed
- `Deployment/k8s-app.yaml`
  - backend image: `<aws-account-id>.dkr.ecr.<aws-region>.amazonaws.com/<backend-repo>:latest`
  - frontend image: `<aws-account-id>.dkr.ecr.<aws-region>.amazonaws.com/<frontend-repo>:latest`

## 2. Create The Cluster

```powershell
eksctl create cluster -f Deployment/eks-cluster.yaml
aws eks update-kubeconfig --region us-east-1 --name ethnography-ai-cluster
```

Use the same region and cluster name from `Deployment/eks-cluster.yaml`.

## 3. Create Backend Secrets

Create these manually in EKS before applying the app manifest:

```powershell
kubectl create namespace ethnography-ai
kubectl create secret generic ethnography-backend-secrets `
  --namespace ethnography-ai `
  --from-literal=AZURE_OPENAI_API_KEY="<your-key>" `
  --from-literal=AZURE_OPENAI_ENDPOINT="<your-endpoint>" `
  --from-literal=AZURE_OPENAI_DEPLOYMENT="gpt-5.4-mini"
```

## 4. Deploy The App

```powershell
kubectl apply -f Deployment/k8s-app.yaml
kubectl get pods -n ethnography-ai
kubectl get service frontend-service -n ethnography-ai
```

Open the external hostname shown for `frontend-service`.

## Updating Existing Deployments

After rebuilding and pushing new Docker images, restart both deployments so EKS pulls the latest image tags:

```powershell
kubectl rollout restart deployment/backend deployment/frontend -n ethnography-ai
kubectl rollout status deployment/backend -n ethnography-ai
kubectl rollout status deployment/frontend -n ethnography-ai
```

If the app gets stuck, check the request path in the logs:

```powershell
kubectl logs deployment/frontend -n ethnography-ai --tail=100
kubectl logs deployment/backend -n ethnography-ai --tail=200
```

## GitHub Actions Deployment

The workflow in `.github/workflows/deploy-cloud-llm.yml` runs on every push to `cloud_llm`.

It performs this sequence:

1. Configure AWS credentials from GitHub Secrets.
2. Build backend and frontend Docker images.
3. Push both images to ECR with the commit SHA and `latest` tags.
4. Create the EKS cluster if it does not already exist.
5. Create or update the Kubernetes Azure OpenAI secret.
6. Apply Kubernetes manifests.
7. Deploy the exact commit-SHA image tags and wait for rollout.

Add these GitHub Secrets:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_MODEL`
