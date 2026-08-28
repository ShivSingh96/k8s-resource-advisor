from dataclasses import dataclass, field


@dataclass
class ContainerMetrics:
    name: str
    cpu_request: float | None    # millicores
    cpu_limit: float | None
    cpu_usage: float | None
    mem_request: float | None    # bytes
    mem_limit: float | None
    mem_usage: float | None

    @property
    def cpu_efficiency(self) -> float | None:
        if self.cpu_request and self.cpu_usage is not None:
            return self.cpu_usage / self.cpu_request
        return None

    @property
    def mem_efficiency(self) -> float | None:
        if self.mem_request and self.mem_usage is not None:
            return self.mem_usage / self.mem_request
        return None

    @property
    def worst_efficiency(self) -> float:
        """Lowest efficiency across CPU and memory — used for sorting."""
        efficiencies = [e for e in (self.cpu_efficiency, self.mem_efficiency) if e is not None]
        return min(efficiencies) if efficiencies else 1.0


@dataclass
class PodMetrics:
    namespace: str
    pod_name: str
    node: str
    containers: list[ContainerMetrics] = field(default_factory=list)
