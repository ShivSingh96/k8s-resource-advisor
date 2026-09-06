# k8s-resource-advisor

Find over-provisioned pods in your Kubernetes cluster. Compares resource **requests**
against live **usage** from metrics-server and surfaces containers running well below
what they reserved.

Read-only. It reports; it never patches a manifest or touches your cluster state.

## Why

The scheduler reserves capacity based on `requests`, not on what a container actually
uses. A container that requests 1 CPU and burns 12 millicores is holding roughly 80×
more than it needs — and the scheduler treats that reservation as real. Multiply it
across a few hundred containers and the effects compound:

- Nodes look full while sitting near-idle, so genuinely hungry pods fail to schedule
- Karpenter and cluster-autoscaler size the fleet to the reservations, not the workload
- You pay for capacity nobody is using

`kubectl top` shows you usage. Pod specs show you requests. Nobody puts them in the same
table and sorts by the worst offender, which is the number you actually need to act on.
That's all this does.

## How it works

```text
For each running pod:
  1. Read resource requests/limits from the pod spec         (CoreV1Api)
  2. Read current CPU and memory usage                       (metrics.k8s.io)
  3. efficiency = usage / request, per container, per resource
  4. Flag anything below the threshold (default 30%)
  5. Sort worst-first, so the top of the table is where the money is
```

If metrics-server isn't installed, it degrades rather than failing: you get requests and
limits, a warning, and no efficiency column.

## Install

```bash
pip install git+https://github.com/ShivSingh96/k8s-resource-advisor.git
```

Or from source:

```bash
git clone https://github.com/ShivSingh96/k8s-resource-advisor
cd k8s-resource-advisor
pip install -e .
```

Requires Python 3.11+, a kubeconfig pointing at a cluster, and
[metrics-server](https://github.com/kubernetes-sigs/metrics-server) for the usage half.

Both `~/.kube/config` and in-cluster service account auth are detected automatically, so
it works the same from a laptop or from inside a pod.

## Usage

```bash
# Every namespace, flag anything under 30% efficiency
k8s-resource-advisor

# One namespace
k8s-resource-advisor -n production

# Stricter: flag anything using less than half its request
k8s-resource-advisor --threshold 0.5

# Show everything, not just the flagged containers
k8s-resource-advisor --all

# Combined
k8s-resource-advisor -n kube-system --all --threshold 0.2
```

| Flag | Default | Effect |
|---|---|---|
| `-n`, `--namespace` | all namespaces | Restrict the scan |
| `--threshold` | `0.3` | Efficiency ratio below which a container is flagged |
| `--all` | off | Print every container, not only the flagged ones |

## Sample output

```text
Scanning all namespaces...
Found 47 containers across 23 running pods

                                         Pod Resource Efficiency
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┓
┃ Namespace  ┃ Pod             ┃ Container ┃ CPU Req ┃ CPU Used ┃ CPU Eff ┃ Mem Req ┃ Mem Used ┃ Mem Eff ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━┩
│ production │ api-server-xk2p │ api       │   1000m │      12m │      1% │   1.0Gi │  180.0Mi │     18% │
│ production │ worker-abc12    │ worker    │    500m │       8m │      2% │ 512.0Mi │   96.0Mi │     19% │
│ staging    │ backend-qq9p    │ backend   │    250m │       5m │      2% │ 256.0Mi │   41.0Mi │     16% │
└────────────┴─────────────────┴───────────┴─────────┴──────────┴─────────┴─────────┴──────────┴─────────┘

Flagged 3 containers below the 30% threshold
(red < 20%, yellow < 50%, green ≥ 50%)
```

## Limitations

Worth reading before you cut anything based on the output.

- **These are point-in-time samples.** metrics-server keeps a short rolling window and no
  history. A batch job between runs, or a service that spikes at 09:00, will look idle
  the moment you scan it. Use this to build a shortlist, then check p95 over a couple of
  weeks in Prometheus before you resize.
- **Low efficiency is not automatically waste.** Headroom for traffic spikes, JVM heap
  sizing, and burst-sensitive workloads are all legitimate reasons to reserve more than
  the steady state. The tool can't tell those apart from genuine over-provisioning.
- **Requests and limits are different problems.** This measures usage against *requests*,
  which is what drives scheduling and node count. Tuning limits is a separate exercise
  with different failure modes — CPU throttling and OOM kills rather than cost.
- **A container with no requests set is skipped.** There's no denominator, so no ratio.
  Those are worth finding too, but that's a different check.

## metrics-server on a local cluster

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# kind and some local clusters serve kubelet certs the metrics-server won't trust
kubectl patch deployment metrics-server -n kube-system \
  --type='json' \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
```

Don't carry that patch into a real cluster — it disables kubelet certificate
verification.

## Architecture

```text
src/k8s_resource_advisor/
├── cli.py          argparse entry point, error handling, exit codes
├── collector.py    CoreV1Api for pod specs + metrics.k8s.io for usage
├── models.py       ContainerMetrics / PodMetrics, with efficiency as properties
├── units.py        parses CPU (n/m/cores) and memory (Ki/Mi/Gi) into comparable numbers
└── reporter.py     rich table, colour-coded by efficiency band
```

`units.py` is where most of the fiddly correctness lives — the Kubernetes API returns CPU
in nanocores from one endpoint and millicores from another, and memory in any of half a
dozen suffixes. It has the test coverage to match.

## Development

```bash
pip install -e .
pip install ruff pytest

ruff check src/ tests/
pytest tests/ -v
```

CI runs the same two commands against Python 3.11 and 3.12 on every push and pull
request.

## License

MIT.
