"""Tests for core network, executive, SLA, and simulation endpoints."""
import pytest
from fastapi import status
from datetime import datetime
from app.models import (
    FiberNodeModel, KPIMetricsModel, AlertModel,
    SelfHealingActionModel, SLAConfigModel, HeadendModel,
    HubModel, SimulationResultModel,
)


@pytest.fixture
def populated_db(db_session):
    """Create a populated database for integration tests."""
    # Create headend
    headend = HeadendModel(
        id=1,
        headend_id="HE-001",
        name="Main Headend",
        region="Northeast",
        city="New York",
        state="NY",
        status="operational",
    )
    db_session.add(headend)

    # Create hub
    hub = HubModel(
        id=1,
        hub_id="HUB-001",
        headend_id="HE-001",
        name="Downtown Hub",
        city="New York",
        state="NY",
        status="operational",
    )
    db_session.add(hub)

    # Create nodes
    for i in range(5):
        node = FiberNodeModel(
            id=i + 1,
            node_id=f"NODE-{i+1:03d}",
            headend_id="HE-001",
            hub_id="HUB-001",
            status="healthy" if i < 3 else ("degraded" if i == 3 else "outage"),
            latitude=40.7 + i * 0.01,
            longitude=-74.0 + i * 0.01,
            region="Northeast",
            city="New York",
            manufacturer="Cisco",
            homes_passed=500,
            homes_active=350,
            docsis_version="3.1",
        )
        db_session.add(node)

        # Add KPIs for each node
        kpi = KPIMetricsModel(
            id=i + 1,
            metric_id=f"KPI-{i+1:03d}",
            node_id=f"NODE-{i+1:03d}",
            timestamp=datetime.now(),
            ds_snr_db=35.0 + i,
            us_snr_db=25.0 + i,
            latency_ms=20.0 + i * 5,
            downstream_throughput_mbps=200.0 - i * 20,
            upstream_throughput_mbps=25.0,
            packet_loss_percent=0.5 + i * 0.3,
            active_modems=350 - i * 20,
            node_cpu_utilization=40.0 + i * 10,
            node_memory_utilization=50.0 + i * 5,
            node_temperature=55.0 + i * 3,
        )
        db_session.add(kpi)

    # Add alerts
    for i in range(3):
        alert = AlertModel(
            id=i + 1,
            alert_id=f"ALT-{i+1:03d}",
            node_id=f"NODE-{i+4:03d}",
            type="HIGH_LATENCY" if i == 0 else "EQUIPMENT_FAILURE",
            severity="CRITICAL" if i == 0 else "WARNING",
            status="ACTIVE",
            description=f"Test alert {i+1}",
            timestamp=datetime.now(),
        )
        db_session.add(alert)

    # Add actions
    action = SelfHealingActionModel(
        id=1,
        action_id="ACT-001",
        node_id="NODE-004",
        alert_id="ALT-001",
        action_type="PARAMETER_OPTIMIZATION",
        status="COMPLETED",
        description="Auto-optimization",
        start_time=datetime.now(),
        effectiveness_score=0.92,
    )
    db_session.add(action)

    # SLA config
    sla = SLAConfigModel(
        id=1,
        config_key="default",
        uptime_target_percent=99.9,
        max_latency_ms=50.0,
        min_throughput_mbps=100.0,
        cost_per_outage_minute=1000.0,
        revenue_per_subscriber_per_hour=0.50,
    )
    db_session.add(sla)

    db_session.commit()
    return db_session


class TestExecutiveEndpoints:
    """Tests for executive dashboard endpoint."""

    def test_get_executive_summary_empty(self, client):
        """Test executive summary with empty database."""
        response = client.get("/api/v1/executive/summary")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_nodes" in data
        assert "network_uptime_percent" in data

    def test_get_executive_summary_with_data(self, client, populated_db):
        """Test executive summary with populated database."""
        response = client.get("/api/v1/executive/summary")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_nodes"] >= 1
        assert "network_uptime_percent" in data
        assert "active_alerts" in data or "total_alerts" in data


class TestSLAEndpoints:
    """Tests for SLA endpoints."""

    def test_get_sla_status_empty(self, client):
        """Test SLA status with no config."""
        response = client.get("/api/v1/sla/status")
        assert response.status_code == status.HTTP_200_OK

    def test_get_sla_status_with_config(self, client, populated_db):
        """Test SLA status with config and data."""
        response = client.get("/api/v1/sla/status")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "config" in data or "status" in data


class TestCoreNetworkEndpoints:
    """Tests for core network endpoints."""

    def test_get_headends_via_core_network(self, client, populated_db):
        """Test the core-network headends endpoint."""
        response = client.get("/api/v1/core-network/headends")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data or "headends" in data or isinstance(data, list)

    def test_get_hubs(self, client, populated_db):
        """Test the core-network hubs endpoint."""
        response = client.get("/api/v1/core-network/hubs")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data or "hubs" in data or isinstance(data, list)


class TestSimulationEndpoints:
    """Tests for simulation/digital twin endpoints."""

    def test_run_simulation_failure(self, client, populated_db):
        """Test running a failure simulation."""
        response = client.post("/api/v1/simulation/run", json={
            "scenario_type": "failure",
            "parameters": {"affected_percent": 10},
        })
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "result_id" in data
        assert "baseline_metrics" in data
        assert "simulated_metrics" in data
        assert "recommended_actions" in data

    def test_run_simulation_capacity(self, client, populated_db):
        """Test running a capacity simulation."""
        response = client.post("/api/v1/simulation/run", json={
            "scenario_type": "capacity",
            "parameters": {"surge_factor": 1.5},
        })
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["simulated_metrics"]["scenario_type"] == "capacity"

    def test_get_simulation_results_empty(self, client):
        """Test getting simulation results when none exist."""
        response = client.get("/api/v1/simulation/results")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0

    def test_simulation_uses_cable_terminology(self, client, populated_db):
        """Test that simulation results use cable network field names."""
        response = client.post("/api/v1/simulation/run", json={
            "scenario_type": "failure",
            "parameters": {"affected_percent": 5},
        })
        data = response.json()
        baseline = data["baseline_metrics"]
        # Should use cable network field names, not telecom
        assert "packet_loss_percent" in baseline or "latency_ms" in baseline
        assert "call_drop_rate" not in baseline
        assert "active_users" not in baseline


class TestWeatherEndpoints:
    """Tests for weather endpoints."""

    def test_get_weather_data(self, client, populated_db):
        """Test getting weather data for a node."""
        response = client.get("/api/v1/weather?node_id=NODE-001")
        # Weather endpoint may return 200 or 404 depending on data availability
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


class TestRetentionEndpoints:
    """Tests for data retention endpoints."""

    def test_get_retention_status(self, client):
        """Test getting retention status."""
        response = client.get("/api/v1/retention/status")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "service_stats" in data or "record_counts" in data


class TestAuthRequirement:
    """Tests that endpoints require API key auth."""

    def test_nodes_requires_api_key(self, db_session):
        """Test that nodes endpoint requires API key."""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.database import get_db

        def override():
            yield db_session

        app.dependency_overrides[get_db] = override
        # Clear startup/shutdown to avoid PostgreSQL connection
        saved_startup = app.router.on_startup[:]
        saved_shutdown = app.router.on_shutdown[:]
        app.router.on_startup.clear()
        app.router.on_shutdown.clear()
        try:
            with TestClient(app) as no_auth_client:
                response = no_auth_client.get("/api/v1/nodes")
                # Should return 401 or 403 without API key
                assert response.status_code in [
                    status.HTTP_401_UNAUTHORIZED,
                    status.HTTP_403_FORBIDDEN,
                ]
        finally:
            app.router.on_startup = saved_startup
            app.router.on_shutdown = saved_shutdown
            app.dependency_overrides.clear()

    def test_health_does_not_require_api_key(self, db_session):
        """Test that health endpoint is public."""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.database import get_db

        def override():
            yield db_session

        app.dependency_overrides[get_db] = override
        # Clear startup/shutdown to avoid PostgreSQL connection
        saved_startup = app.router.on_startup[:]
        saved_shutdown = app.router.on_shutdown[:]
        app.router.on_startup.clear()
        app.router.on_shutdown.clear()
        try:
            with TestClient(app) as no_auth_client:
                response = no_auth_client.get("/health")
                assert response.status_code == status.HTTP_200_OK
        finally:
            app.router.on_startup = saved_startup
            app.router.on_shutdown = saved_shutdown
            app.dependency_overrides.clear()
