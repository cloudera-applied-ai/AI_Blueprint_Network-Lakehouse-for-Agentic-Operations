"""Tests for API endpoints."""
import pytest
from fastapi import status


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check_returns_ok(self, client):
        """Test that health endpoint returns 200 OK."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Status can be "healthy" or "starting" depending on initialization state
        assert data["status"] in ["healthy", "starting"]


class TestNodeEndpoints:
    """Tests for node-related endpoints."""

    def test_get_nodes_empty(self, client):
        """Test getting nodes when none exist."""
        response = client.get("/api/v1/nodes")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_get_nodes_with_data(self, client, sample_node):
        """Test getting nodes when data exists."""
        response = client.get("/api/v1/nodes")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["node_id"] == "TWR-TEST-001"

    def test_get_nodes_with_limit(self, client, sample_node):
        """Test node pagination with limit."""
        response = client.get("/api/v1/nodes?limit=10")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data

    def test_get_node_by_id(self, client, sample_node):
        """Test getting a specific node by ID."""
        response = client.get(f"/api/v1/nodes/{sample_node.node_id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["node_id"] == sample_node.node_id

    def test_get_node_not_found(self, client):
        """Test getting a non-existent node."""
        response = client.get("/api/v1/nodes/NONEXISTENT")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAlertEndpoints:
    """Tests for alert-related endpoints."""

    def test_get_alerts_empty(self, client):
        """Test getting alerts when none exist."""
        response = client.get("/api/v1/alerts")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0

    def test_get_alerts_with_data(self, client, sample_alert):
        """Test getting alerts when data exists."""
        response = client.get("/api/v1/alerts")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["alert_id"] == "ALT-TEST-001"

    def test_get_alerts_filter_by_severity(self, client, sample_alert):
        """Test filtering alerts by severity."""
        response = client.get("/api/v1/alerts?severity=WARNING")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1

        response = client.get("/api/v1/alerts?severity=CRITICAL")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0


class TestActionEndpoints:
    """Tests for action-related endpoints."""

    def test_get_actions_empty(self, client):
        """Test getting actions when none exist."""
        response = client.get("/api/v1/actions")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0

    def test_get_actions_with_data(self, client, sample_action):
        """Test getting actions when data exists."""
        response = client.get("/api/v1/actions")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["action_id"] == "ACT-TEST-001"

    def test_get_actions_filter_by_status(self, client, sample_action):
        """Test filtering actions by status."""
        response = client.get("/api/v1/actions?status=COMPLETED")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1


class TestKPIEndpoints:
    """Tests for KPI-related endpoints."""

    def test_get_kpis_empty(self, client):
        """Test getting KPIs when none exist."""
        response = client.get("/api/v1/kpis")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0

    def test_get_kpis_with_data(self, client, sample_kpi):
        """Test getting KPIs when data exists."""
        response = client.get("/api/v1/kpis")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1


class TestSystemEndpoints:
    """Tests for system control endpoints."""

    def test_get_system_status(self, client):
        """Test getting system status."""
        response = client.get("/api/v1/system/status")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Check for nested structure
        assert "data_generation" in data or "paused" in data
        assert "timestamp" in data


class TestStatsEndpoint:
    """Tests for statistics endpoint."""

    def test_get_stats(self, client):
        """Test getting stats."""
        response = client.get("/api/v1/stats")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Check for expected keys (may be named differently)
        assert "nodes" in data or "kpi_metrics" in data
        assert "timestamp" in data
