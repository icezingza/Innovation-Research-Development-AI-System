#!/bin/sh
# deploy_k8s.sh: Deploy IRD-AI to Kubernetes using Helm

NAMESPACE="ird-ai"
echo "Creating namespace: $NAMESPACE..."
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

echo "Deploying IRD-AI via Helm..."
helm install ird-ai ./helm/ird-ai -n $NAMESPACE -f ./helm/ird-ai/values.yaml

echo "Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l app=ird-ai -n $NAMESPACE --timeout=300s

echo "Deployment complete! Status:"
kubectl get pods -n $NAMESPACE

echo "Forwarding API to port 8000..."
kubectl port-forward -n $NAMESPACE svc/ird-ai-app 8000:8000
