import pytest

from k8s_resource_advisor.units import format_cpu, format_memory, parse_cpu, parse_memory


class TestParseCpu:
    def test_millicores(self):
        assert parse_cpu("100m") == 100.0

    def test_whole_cores(self):
        assert parse_cpu("2") == 2000.0

    def test_nanocores(self):
        assert parse_cpu("500000000n") == pytest.approx(500.0, rel=1e-3)

    def test_fractional_cores(self):
        assert parse_cpu("0.5") == 500.0

    def test_none(self):
        assert parse_cpu(None) is None


class TestParseMemory:
    def test_mebibytes(self):
        assert parse_memory("128Mi") == 128 * 1024**2

    def test_gibibytes(self):
        assert parse_memory("1Gi") == 1024**3

    def test_kibibytes(self):
        assert parse_memory("512Ki") == 512 * 1024

    def test_plain_bytes(self):
        assert parse_memory("1024") == 1024.0

    def test_megabytes(self):
        assert parse_memory("100M") == 100 * 1000**2

    def test_none(self):
        assert parse_memory(None) is None


class TestFormatCpu:
    def test_millicores(self):
        assert format_cpu(250.0) == "250m"

    def test_cores(self):
        assert format_cpu(1500.0) == "1.50"

    def test_none(self):
        assert format_cpu(None) == "—"


class TestFormatMemory:
    def test_mebibytes(self):
        assert format_memory(128 * 1024**2) == "128.0Mi"

    def test_gibibytes(self):
        assert format_memory(2 * 1024**3) == "2.0Gi"

    def test_none(self):
        assert format_memory(None) == "—"


class TestContainerEfficiency:
    def test_cpu_efficiency(self):
        from k8s_resource_advisor.models import ContainerMetrics
        c = ContainerMetrics(
            name="app",
            cpu_request=1000.0, cpu_limit=2000.0, cpu_usage=100.0,
            mem_request=None,   mem_limit=None,   mem_usage=None,
        )
        assert c.cpu_efficiency == pytest.approx(0.1)

    def test_efficiency_none_when_no_request(self):
        from k8s_resource_advisor.models import ContainerMetrics
        c = ContainerMetrics(
            name="app",
            cpu_request=None, cpu_limit=None, cpu_usage=100.0,
            mem_request=None, mem_limit=None, mem_usage=None,
        )
        assert c.cpu_efficiency is None

    def test_efficiency_none_when_no_usage(self):
        from k8s_resource_advisor.models import ContainerMetrics
        c = ContainerMetrics(
            name="app",
            cpu_request=1000.0, cpu_limit=None, cpu_usage=None,
            mem_request=None,   mem_limit=None,  mem_usage=None,
        )
        assert c.cpu_efficiency is None
