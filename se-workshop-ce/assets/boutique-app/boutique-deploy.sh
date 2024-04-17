#!/bin/bash

echo "Getting cluster credentials..."
gcloud container clusters get-credentials $GKE_CLUSTER_NAME --region us-central1-a
kubectl config rename-context $(kubectl config current-context) boutique
kubectl config use-context boutique

# Validating cluster is ready
echo "Checking if the cluster nodes are ready..."
until kubectl get nodes | grep ' Ready'; do
    echo "Waiting for all nodes to be in the Ready state..."
    sleep 10
done
echo "All nodes are ready."

### Deploy Boutique App and Monitoring
echo "Deploying boutique-app..."
kubectl create namespace boutique-app
kubectl -n boutique-app apply -f /root/boutique-app/boutique-app.yaml

# Add Labels to Deployments
DEPLOYMENTS=(adservice cartservice checkoutservice currencyservice emailservice frontend loadgenerator paymentservice productcatalogservice recommendationservice redis-cart shippingservice)
for dep in "${DEPLOYMENTS[@]}"; do
  kubectl -n boutique-app patch deployment "$dep" -p "{\"metadata\":{\"labels\":{\"app\":\"$dep\"}}}"
done

# Update Image for Frontend
kubectl -n boutique-app patch deployment frontend -p '{"spec":{"template":{"spec":{"containers":[{"name":"server","image":"aady12/boutique-frontend:ci"}]}}}}'

# Deploy Monitoring
echo "Deploying boutique-monitoring..."
kubectl -n boutique-app apply -f /root/boutique-app/boutique-monitoring.yaml
