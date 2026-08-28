# k8s-resource-advisor

Find over-provisioned pods in your Kubernetes cluster. Compares resource *requests* against live *usage* (via metrics-server) and surfaces containers running well below their allocated CPU and memory.

Built from real-world experience reducing cloud infrastructure costs by $180K–$300K/year through Karpenter right-sizing at SurveyMonkey.

## Problem

Kubernetes schedulers reserve resources based on `requests`, not actual usage. Over-provisioned pods hold capacity that prevents other workloads from scheduling, leading to:

- Wasted node capacity → more nodes needed → higher cost
- Karpenter and cluster-autoscaler provision larger nodes than necessary
- 22 nodes at 2% CPU utilization = paying for 22 nodes to run 0.44 nodes' worth of work

## How it works

```
For each running pod:
  1. Fetch resource requests/limits from pod spec (via K8s API)
  2. Fetch current CPU and memory usage (via metrics.k8s.io API)
  3. Calculate efficiency = usage / request
  4. Flag containers below the threshold (default: 30%)
  5. Sort by worst efficiency first
```

## Installation

```bash
pip install k8s-resource-advisor
```

Or from source:

```bash
git clone https://github.com/ShivSingh96/k8s-resource-advisor
cd k8s-resource-advisor
pip install -e .
```

Requires: Python 3.11+, a kubeconfig pointing at your cluster, and [metrics-server](https://github.com/kubernetes-sigs/metrics-server) installed.

## Usage

```bash
# Scan all namespaces, flag anything below 30% efficiency
k8s-resource-advisor

# Scan a specific namespace
k8s-resource-advisor -n production

# Change the threshold (50% = flag anything using less than half its request)
k8s-resource-advisor --threshold 0.5

# Show all containers, not just flagged ones
k8s-resource-advisor --all

# Combine flags
k8s-resource-advisor -n kube-system --all --threshold 0.2
```

## Sample output

```
Scanning all namespaces...
Found 47 containers across 23 running pods

⚠ metrics-server not available — showing requests/limits only, no live usage data.

╭──────────────────────────────────────────────────────────────────────────────────────╮
│                          Pod Resource Efficiency                                      │
├─────────────┬──────────────────┬───────────┬─────────┬──────────┬────────┬──────────┤
│ Namespace   │ Pod              │ Container │ CPU Req │ CPU Used │ CPU Eff│ Mem Req  │
├─────────────┼──────────────────┼───────────┼─────────┼──────────┼────────┼──────────┤
│ production  │ api-server-xk2p  │ api       │ 1.00    │ 12m      │ 1%     │ 1.0Gi   │
│ production  │ worker-abc12     │ worker    │ 500m    │ 8m       │ 2%     │ 512.0Mi │
│ staging     │ backend-qq9p     │ backend   │ 250m    │ 5m       │ 2%     │ 256.0Mi │
╰─────────────┴──────────────────┴───────────┴─────────┴──────────┴────────┴──────────╯

Flagged: 3 containers below 30% threshold  (red < 20%, yellow < 50%, green ≥ 50%)
```

## Install metrics-server (kind/local clusters)

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# For kind clusters, patch to disable TLS verification:
kubectl patch deployment metrics-server -n kube-system \
  --type='json' \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
```

## Architecture

```
cli.py          argparse entry point
collector.py    queries K8s CoreV1Api (pod specs) + metrics.k8s.io (usage)
models.py       ContainerMetrics, PodMetrics dataclasses with efficiency properties
units.py        CPU (nanocores/millicores/cores) and memory (Ki/Mi/Gi) parsers
reporter.py     rich table output with color-coded efficiency percentages
```

Works with both local kubeconfig (`~/.kube/config`) and in-cluster service account (automatically detected).

## Development

```bash
pip install -e ".[dev]"
ruff check src/ tests/
pytest tests/ -v
```
