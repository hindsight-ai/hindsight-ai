#!/bin/bash

echo "--- Kubernetes Cluster Status ---"

echo "1. Node Status:"
kubectl get nodes

echo -e "\n2. Pod Status (all namespaces):"
kubectl get pods --all-namespaces

echo -e "\n3. Deployment Status (default namespace):"
kubectl get deployments -n default

echo -e "\n4. Service Status (default namespace):"
kubectl get services -n default

echo -e "\n5. Ingress Status (default namespace):"
kubectl get ingress -n default

echo -e "\n--- End of Kubernetes Cluster Status ---"
