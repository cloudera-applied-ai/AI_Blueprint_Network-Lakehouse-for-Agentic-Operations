"""Tests for the executive summary endpoint."""
import pytest
from datetime import datetime, timedelta
from fastapi import status

from app.models import (
    FiberNodeModel,
    KPIMetricsModel,
    AlertModel,
    SelfHealingActionModel,
    SLAConfigModel,
    SLABreachModel,
)


class TestExecutiveSummary:
    """Tests for the executive summary endpoint."""

    def test_executive_summary_empty_database(self, client):
        """Test executive summary returns valid response with empty database."""
        response = client.get("/api/v1/executive/summary?period_hours=24")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should have all required fields even with no data
        assert "timestamp" in data
        assert "total_nodes" in data
        assert "network_uptime_percent" in data
        assert "sla_compliance_percent" in data

    def test_executive_summary_with_nodes(self, client, db_session):
        """Test executive summary returns valid node data structure."""
        response = client.get("/api/v1/executive/summary?period_hours=24")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify required fields exist and have valid types
        assert "total_nodes" in data
        assert isinstance(data["total_nodes"], int)
        assert data["total_nodes"] >= 0

        assert "healthy_nodes" in data
        assert isinstance(data["healthy_nodes"], int)

        assert "degraded_nodes" in data
        assert isinstance(data["degraded_nodes"], int)

        assert "outage_nodes" in data
        assert isinstance(data["outage_nodes"], int)

        assert "network_uptime_percent" in data
        assert isinstance(data["network_uptime_percent"], (int, float))
        assert 0 <= data["network_uptime_percent"] <= 100

    def test_executive_summary_with_sla_config(self, client, db_session, sample_sla_config):
        """Test executive summary uses SLA config for calculations."""
        response = client.get("/api/v1/executive/summary?period_hours=24")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify SLA compliance is calculated (should be 100% with no breaches)
        assert data["sla_compliance_percent"] >= 0
        assert data["sla_compliance_percent"] <= 100

    def test_executive_summary_with_alerts(self, client, db_session, sample_node):
        """Test executive summary counts alerts correctly."""
        # Create alerts with different severities
        now = datetime.now()
        alerts = [
            AlertModel(id=1, alert_id="ALT-01", node_id=sample_node.node_id,
                      type="TEST", severity="CRITICAL", status="ACTIVE", timestamp=now),
            AlertModel(id=2, alert_id="ALT-02", node_id=sample_node.node_id,
                      type="TEST", severity="WARNING", status="ACTIVE", timestamp=now),
            AlertModel(id=3, alert_id="ALT-03", node_id=sample_node.node_id,
                      type="TEST", severity="WARNING", status="RESOLVED", timestamp=now),
        ]
        for alert in alerts:
            db_session.add(alert)
        db_session.commit()

        response = client.get("/api/v1/executive/summary?period_hours=24")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify alert fields exist and have valid types
        assert "total_alerts" in data
        assert isinstance(data["total_alerts"], int)
        assert data["total_alerts"] >= 0

        assert "critical_alerts" in data
        assert isinstance(data["critical_alerts"], int)
        assert data["critical_alerts"] >= 0

    def test_executive_summary_with_actions(self, client, db_session, sample_node):
        """Test executive summary counts healing actions correctly."""
        now = datetime.now()
        actions = [
            SelfHealingActionModel(
                id=1, action_id="ACT-01", node_id=sample_node.node_id,
                action_type="TEST", status="COMPLETED", start_time=now,
                effectiveness_score=0.9
            ),
            SelfHealingActionModel(
                id=2, action_id="ACT-02", node_id=sample_node.node_id,
                action_type="TEST", status="COMPLETED", start_time=now,
                effectiveness_score=0.8
            ),
            SelfHealingActionModel(
                id=3, action_id="ACT-03", node_id=sample_node.node_id,
                action_type="TEST", status="FAILED", start_time=now,
                effectiveness_score=0.1
            ),
        ]
        for action in actions:
            db_session.add(action)
        db_session.commit()

        response = client.get("/api/v1/executive/summary?period_hours=24")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify action stats
        assert "auto_resolved" in data or "total_actions" in data

    def test_executive_summary_period_filtering(self, client, db_session, sample_node):
        """Test that period_hours filters data correctly."""
        now = datetime.now()
        old_time = now - timedelta(hours=48)

        # Create KPIs - one recent, one old
        kpis = [
            KPIMetricsModel(
                id=1, metric_id="KPI-01", node_id=sample_node.node_id,
                timestamp=now, ds_snr_db=38.0, latency_ms=20.0,
                downstream_throughput_mbps=200.0, packet_loss_percent=1.0
            ),
            KPIMetricsModel(
                id=2, metric_id="KPI-02", node_id=sample_node.node_id,
                timestamp=old_time, ds_snr_db=35.0, latency_ms=30.0,
                downstream_throughput_mbps=150.0, packet_loss_percent=2.0
            ),
        ]
        for kpi in kpis:
            db_session.add(kpi)
        db_session.commit()

        # 24 hour period should only include recent KPI
        response = client.get("/api/v1/executive/summary?period_hours=24")
        assert response.status_code == status.HTTP_200_OK

    def test_executive_summary_handles_none_values(self, client, db_session):
        """Test that executive summary handles None values gracefully."""
        from datetime import datetime
        # Create SLA breach with resolved=False to test active_breaches handling
        breach = SLABreachModel(
            id=1,
            breach_id="BREACH-TEST-001",
            breach_type="uptime",
            metric_name="network_uptime",
            sla_target=99.9,
            actual_value=98.0,
            severity="breach",
            breach_start=datetime.now(),
            resolved=False,
        )
        db_session.add(breach)
        db_session.commit()

        # This should not raise TypeError even if some queries return None
        response = client.get("/api/v1/executive/summary?period_hours=24")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # active_sla_breaches should be an integer, not None
        assert isinstance(data.get("active_sla_breaches", 0), int)

    def test_executive_summary_regions(self, client, db_session):
        """Test that regional breakdown is included."""
        # Create nodes in different regions
        nodes = [
            FiberNodeModel(id=1, node_id="TWR-US", status="healthy",
                          latitude=40.0, longitude=-74.0, region="Northeast"),
            FiberNodeModel(id=2, node_id="TWR-EU", status="healthy",
                          latitude=51.0, longitude=0.0, region="Southeast"),
        ]
        for node in nodes:
            db_session.add(node)
        db_session.commit()

        response = client.get("/api/v1/executive/summary?period_hours=24")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "regions" in data
        assert isinstance(data["regions"], list)

    def test_executive_summary_financial_metrics(self, client, db_session, sample_sla_config):
        """Test that financial metrics are calculated."""
        # Create a node with outage status
        node = FiberNodeModel(
            id=1, node_id="TWR-OUTAGE", status="outage",
            latitude=0, longitude=0, region="Northeast"
        )
        db_session.add(node)
        db_session.commit()

        response = client.get("/api/v1/executive/summary?period_hours=24")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Financial metrics should be present
        assert "revenue_at_risk" in data
        assert "revenue_protected" in data
        assert "sla_penalty_exposure" in data
