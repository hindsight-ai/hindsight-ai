#!/bin/bash

echo "--- Traefik Ingress Status ---"

echo "1. Traefik Pods Status (kube-system namespace):"
kubectl get pods -n kube-system -l app.kubernetes.io/name=traefik

echo -e "\n2. Traefik IngressRoutes (default namespace):"
kubectl get ingressroutes -n default

echo -e "\n3. Traefik Middlewares (default namespace):"
kubectl get middlewares -n default

echo -e "\n4. Describe Hindsight Dashboard IngressRoute:"
kubectl describe ingressroute hindsight-dashboard-ingress-domain -n default

echo -e "\n5. Describe Hindsight Service IngressRoute:"
kubectl describe ingressroute hindsight-service-ingress-domain -n default

echo -e "\n--- End of Traefik Ingress Status ---"
