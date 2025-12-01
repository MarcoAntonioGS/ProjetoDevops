<#
Helper script for Docker Desktop Kubernetes users.
What it does:
 - checks kubectl context (suggests switching to 'docker-desktop')
 - builds the local Docker image `school_scheduler-app:latest`
 - applies the k8s manifests under `k8s/`
 - restarts the `school-scheduler` deployment and tails pods

Run from repository root in PowerShell:
  .\scripts\deploy-docker-desktop.ps1

Note: Docker Desktop's Kubernetes uses the same Docker engine, so local images are available
without loading them into a separate cluster runtime.
#>

param(
  [switch]$SkipBuild,
  [switch]$DryRun
)

function Fail($msg) {
  Write-Host "ERROR: $msg" -ForegroundColor Red
  exit 1
}

# Helper: run a command or print it when DryRun is set
function RunCommand($command, [string[]]$args) {
  $cmdLine = "$command $($args -join ' ')"
  if ($DryRun) {
    Write-Host "DRY-RUN: $cmdLine" -ForegroundColor Yellow
    return 0
  }
  Write-Host "Running: $cmdLine"
  & $command @args
  $rc = $LASTEXITCODE
  return $rc
}

Write-Host "== Deploy helper for Docker Desktop Kubernetes =="

# Ensure kubectl is available
if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
  Fail "kubectl not found in PATH. Install kubectl and try again."
}

$current = kubectl config current-context 2>$null
if (-not $current) {
  Write-Host "No current kubectl context found. Please ensure Docker Desktop Kubernetes is enabled and kubectl is configured." -ForegroundColor Yellow
} else {
  Write-Host "Current kubectl context: $current"
}

# Prefer docker-desktop context
if ($current -ne 'docker-desktop') {
  Write-Host "Switching to 'docker-desktop' context if available..."
  $contexts = kubectl config get-contexts -o name 2>$null | Select-String -Pattern '^docker-desktop$' -Quiet
  if ($contexts) {
    kubectl config use-context docker-desktop | Out-Null
    Write-Host "Switched to docker-desktop"
  } else {
    Write-Host "Warning: 'docker-desktop' context not found. Continuing with current context: $current" -ForegroundColor Yellow
  }
}

if (-not $SkipBuild) {
  Write-Host "Building Docker image: school_scheduler-app:latest"
  $rc = RunCommand 'docker' @('build','-t','school_scheduler-app:latest','.')
  if ($rc -ne 0) { Fail "Docker build failed." }
}

Write-Host "Applying Kubernetes manifests in ./k8s/..."
$rc = RunCommand 'kubectl' @('apply','-f','.\k8s\namespace-dev.yaml')
if ($rc -ne 0) { Fail "kubectl apply namespace failed." }
$rc = RunCommand 'kubectl' @('apply','-f','.\k8s\secret-example.yaml')
if ($rc -ne 0) { Fail "kubectl apply secret failed." }
$rc = RunCommand 'kubectl' @('apply','-f','.\k8s\mysql-headless-svc.yaml')
if ($rc -ne 0) { Fail "kubectl apply mysql service failed." }
$rc = RunCommand 'kubectl' @('apply','-f','.\k8s\mysql-statefulset.yaml')
if ($rc -ne 0) { Fail "kubectl apply mysql statefulset failed." }
$rc = RunCommand 'kubectl' @('apply','-f','.\k8s\app-deployment-dev.yaml')
if ($rc -ne 0) { Fail "kubectl apply app deployment failed." }
$rc = RunCommand 'kubectl' @('apply','-f','.\k8s\app-service-dev.yaml')
if ($rc -ne 0) { Fail "kubectl apply app service failed." }

Write-Host "Restarting deployment to pick up local image (if necessary)"
$rc = RunCommand 'kubectl' @('rollout','restart','deployment/school-scheduler','-n','school-scheduler-dev')
if ($rc -ne 0) { Fail "kubectl rollout restart failed." }

Write-Host "Watching pods in namespace school-scheduler-dev (Ctrl+C to stop)"
RunCommand 'kubectl' @('get','pods','-n','school-scheduler-dev','-w')
