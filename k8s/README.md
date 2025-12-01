Kubernetes - minimal dev manifests
=================================

Files in this folder are a minimal, opinionated starting point to run the project in
a local Kubernetes cluster (kind, minikube, k3d).

Included manifests (dev):

- `namespace-dev.yaml` - dedicated namespace for dev resources
- `secret-example.yaml` - example Secret (do NOT commit real secrets; prefer `kubectl create secret`)
- `mysql-headless-svc.yaml` - headless Service used by the MySQL StatefulSet
- `mysql-statefulset.yaml` - MySQL StatefulSet with PVC template (1Gi request)
- `app-deployment-dev.yaml` - Deployment for the application (uses Secret for DB creds)
- `app-service-dev.yaml` - ClusterIP Service to expose the app within the cluster

Quick dev workflow (kind)
-------------------------
1. Create a kind cluster and context (https://kind.sigs.k8s.io/):

   kind create cluster --name school-dev

2. Apply manifests (for local dev):

   kubectl apply -f k8s/namespace-dev.yaml
   kubectl apply -f k8s/secret-example.yaml
   kubectl apply -f k8s/mysql-headless-svc.yaml
   kubectl apply -f k8s/mysql-statefulset.yaml
   kubectl apply -f k8s/app-deployment-dev.yaml
   kubectl apply -f k8s/app-service-dev.yaml

3. Accessing the DB from host:
   - Use `kubectl port-forward svc/mysql 3306:3306 -n school-scheduler-dev` and connect to localhost:3306

Notes & adjustments
-------------------
- The application in this repo is primarily a CLI/GUI Python app (Tk). It does not provide an HTTP
  server by default. If you run it inside Kubernetes, consider one of these options:
  - Run the app as a Job/CronJob for headless schedule generation.
  - Add a small HTTP health endpoint to the app and enable readiness/liveness probes.
  - Use `kubectl exec` into the pod to run the CLI actions on-demand.

- For production consider:
  - Using a managed database or a proper MySQL StatefulSet with backups and stable StorageClass.
  - Using a Secret manager (Vault, SealedSecrets, SOPS) instead of committing secrets.
  - Adding Ingress + TLS via cert-manager, and resource autoscaling.
