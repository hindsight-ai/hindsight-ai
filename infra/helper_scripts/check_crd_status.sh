#!/bin/bash

echo "--- Custom Resource Definition (CRD) Status ---"

CRDS=("middlewares.traefik.io" "ingressroutes.traefik.io" "ingressroutetcps.traefik.io" "ingressrouteudps.traefik.io" "tlsoptions.traefik.io" "tlsstores.traefik.io" "traefikservices.traefik.io")

for crd in "${CRDS[@]}"; do
    echo -e "\nChecking CRD: $crd"
    kubectl get crd "$crd" -o jsonpath='{.status.conditions[?(@.type=="Established")].status}' | grep -q "True"
    if [ $? -eq 0 ]; then
        echo "  Status: Established"
    else
        echo "  Status: Not Established or Not Found"
        kubectl get crd "$crd" || true # Show error if not found
    fi
done

echo -e "\n--- End of CRD Status Check ---"
