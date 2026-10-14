"""Tests for configuration management API endpoints."""
import pytest


class TestDeviceSummary:
    def test_device_summary_empty(self, client):
        resp = client.get("/api/v1/config/devices/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_devices"] == 0
        assert data["compliance_rate"] == 100.0

    def test_device_summary_with_device(self, client, sample_network_device):
        resp = client.get("/api/v1/config/devices/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_devices"] == 1
        assert "firewall" in data["by_type"]
        assert data["drift_count"] == 0


class TestDeviceList:
    def test_list_devices_empty(self, client):
        resp = client.get("/api/v1/config/devices")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["devices"] == []

    def test_list_devices_with_device(self, client, sample_network_device):
        resp = client.get("/api/v1/config/devices")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["devices"][0]["device_id"] == "FW-TEST-001"

    def test_list_devices_filter_type(self, client, sample_network_device):
        resp = client.get("/api/v1/config/devices?device_type=firewall")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

        resp = client.get("/api/v1/config/devices?device_type=switch")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_devices_filter_status(self, client, sample_network_device):
        resp = client.get("/api/v1/config/devices?status=operational")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_devices_filter_region(self, client, sample_network_device):
        resp = client.get("/api/v1/config/devices?region=Northeast")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


class TestDeviceDetail:
    def test_device_detail(self, client, sample_network_device):
        resp = client.get(f"/api/v1/config/devices/{sample_network_device.device_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["device"]["device_id"] == "FW-TEST-001"
        assert data["device"]["manufacturer"] == "Fortinet"
        assert "recent_changes" in data
        assert "compliance_history" in data

    def test_device_detail_not_found(self, client):
        resp = client.get("/api/v1/config/devices/NONEXISTENT")
        assert resp.status_code == 404


class TestDeviceSync:
    def test_sync_device(self, client, sample_network_device):
        resp = client.post(f"/api/v1/config/devices/{sample_network_device.device_id}/sync")
        assert resp.status_code == 200
        assert resp.json()["status"] == "synced"

    def test_sync_device_not_found(self, client):
        resp = client.post("/api/v1/config/devices/NONEXISTENT/sync")
        assert resp.status_code == 404


class TestTemplates:
    def test_list_templates_empty(self, client):
        resp = client.get("/api/v1/config/templates")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_templates_with_template(self, client, sample_config_template):
        resp = client.get("/api/v1/config/templates")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_templates_filter_type(self, client, sample_config_template):
        resp = client.get("/api/v1/config/templates?device_type=firewall")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

        resp = client.get("/api/v1/config/templates?device_type=switch")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_create_template(self, client):
        resp = client.post("/api/v1/config/templates?name=Test%20Template&device_type=switch&device_role=core")
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] is True
        assert "template_id" in data


class TestChangeLog:
    def test_list_changes_empty(self, client):
        resp = client.get("/api/v1/config/changes")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    def test_rollback_change_not_found(self, client):
        resp = client.post("/api/v1/config/changes/NONEXISTENT/rollback")
        assert resp.status_code == 404


class TestComplianceSummary:
    def test_compliance_summary_empty(self, client):
        resp = client.get("/api/v1/config/compliance/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_compliance_rate"] == 100.0

    def test_compliance_summary_with_device(self, client, sample_network_device):
        resp = client.get("/api/v1/config/compliance/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["totals"]["compliant"] == 1

    def test_compliance_scan(self, client, sample_network_device):
        resp = client.post("/api/v1/config/compliance/scan")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["devices_scanned"] == 1


class TestChangeRequests:
    def test_list_change_requests_empty(self, client):
        resp = client.get("/api/v1/config/change-requests")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_change_requests_with_request(self, client, sample_change_request):
        resp = client.get("/api/v1/config/change-requests")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["requests"][0]["request_id"] == "CR-TEST-001"

    def test_create_change_request(self, client, sample_network_device):
        resp = client.post(
            "/api/v1/config/change-requests"
            "?title=Update%20ACLs"
            "&change_type=security"
            f"&device_ids={sample_network_device.device_id}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending_review"
        assert data["device_count"] == 1

    def test_create_change_request_missing_device(self, client):
        resp = client.post(
            "/api/v1/config/change-requests"
            "?title=Test&change_type=maintenance&device_ids=NONEXISTENT"
        )
        assert resp.status_code == 404

    def test_approve_change_request(self, client, sample_change_request):
        resp = client.put(
            f"/api/v1/config/change-requests/{sample_change_request.request_id}"
            "?status=approved&approved_by=admin"
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

    def test_invalid_transition(self, client, sample_change_request):
        resp = client.put(
            f"/api/v1/config/change-requests/{sample_change_request.request_id}"
            "?status=completed"
        )
        assert resp.status_code == 400

    def test_change_request_not_found(self, client):
        resp = client.put("/api/v1/config/change-requests/NONEXISTENT?status=approved")
        assert resp.status_code == 404


class TestChangeRequestExecution:
    def test_execute_approved_request(self, client, sample_change_request):
        # First approve
        client.put(
            f"/api/v1/config/change-requests/{sample_change_request.request_id}"
            "?status=approved&approved_by=admin"
        )
        # Then execute
        resp = client.post(
            f"/api/v1/config/change-requests/{sample_change_request.request_id}/execute"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert len(data["execution_log"]) == 1
        assert data["execution_log"][0]["status"] == "applied"

    def test_execute_unapproved_request(self, client, sample_change_request):
        resp = client.post(
            f"/api/v1/config/change-requests/{sample_change_request.request_id}/execute"
        )
        assert resp.status_code == 400

    def test_full_lifecycle(self, client, sample_network_device):
        """Test create -> approve -> execute -> verify change log"""
        # Create
        resp = client.post(
            "/api/v1/config/change-requests"
            "?title=Full%20Lifecycle%20Test"
            "&change_type=maintenance"
            f"&device_ids={sample_network_device.device_id}"
        )
        assert resp.status_code == 200
        request_id = resp.json()["request_id"]

        # Approve
        resp = client.put(f"/api/v1/config/change-requests/{request_id}?status=approved&approved_by=admin")
        assert resp.status_code == 200

        # Execute
        resp = client.post(f"/api/v1/config/change-requests/{request_id}/execute")
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

        # Verify change log was created
        resp = client.get(f"/api/v1/config/changes?device_id={sample_network_device.device_id}")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

        # Verify device detail shows change
        resp = client.get(f"/api/v1/config/devices/{sample_network_device.device_id}")
        assert resp.status_code == 200
        assert len(resp.json()["recent_changes"]) >= 1
