#!/bin/bash

echo "--- Traefik Ingress Status ---"

echo "1. Traefik Pods Status (kube-system namespace):"
kubectl get pods -n kube-system -l app.kubernetes.io/name=traefik

echo -e "\n2. Traefik IngressRoutes (all namespaces - traefik.io):"
kubectl get ingressroutes.traefik.io --all-namespaces

echo -e "\n3. Traefik Middlewares (all namespaces - traefik.io):"
kubectl get middlewares.traefik.io --all-namespaces

echo -e "\n4. Describe Hindsight Dashboard IngressRoute (traefik.io):"
kubectl describe ingressroute.traefik.io hindsight-dashboard-ingress-domain -n default

echo -e "\n5. Describe Hindsight Service IngressRoute (traefik.io):"
kubectl describe ingressroute.traefik.io hindsight-service-ingress-domain -n default

echo -e "\n--- End of Traefik Ingress Status ---"
