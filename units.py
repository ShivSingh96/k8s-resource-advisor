"""CPU and memory unit parsing/formatting for Kubernetes resource values."""


def parse_cpu(value: str | None) -> float | None:
    """Parse a Kubernetes CPU string to millicores."""
    if value is None:
        return None
    if value.endswith("n"):        # nanocores  e.g. "500000000n"
        return float(value[:-1]) / 1_000_000
    if value.endswith("m"):        # millicores e.g. "100m"
        return float(value[:-1])
    return float(value) * 1000     # whole cores e.g. "1" → 1000m


def parse_memory(value: str | None) -> float | None:
    """Parse a Kubernetes memory string to bytes."""
    if value is None:
        return None
    for suffix, mult in [
        ("Ki", 1024), ("Mi", 1024**2), ("Gi", 1024**3), ("Ti", 1024**4),
        ("K", 1000),  ("M", 1000**2),  ("G", 1000**3),
    ]:
        if value.endswith(suffix):
            return float(value[: -len(suffix)]) * mult
    return float(value)


def format_cpu(millicores: float | None) -> str:
    if millicores is None:
        return "—"
    if millicores >= 1000:
        return f"{millicores / 1000:.2f}"
    return f"{millicores:.0f}m"


def format_memory(bytes_val: float | None) -> str:
    if bytes_val is None:
        return "—"
    for unit, size in [("Gi", 1024**3), ("Mi", 1024**2), ("Ki", 1024)]:
        if bytes_val >= size:
            return f"{bytes_val / size:.1f}{unit}"
    return f"{bytes_val:.0f}B"
