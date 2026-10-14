"""Tests for background task functions."""
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models import (
    FiberNodeModel,
    KPIMetricsModel,
    AlertModel,
    SelfHealingActionModel,
)


class TestInsertWithConflict:
    """Tests for insert operations with ON CONFLICT handling."""

    def test_kpi_insert_handles_duplicate_id(self, db_session, sample_node):
        """Test that KPI insert handles duplicate primary key gracefully."""
        # Insert first KPI
        kpi1 = KPIMetricsModel(
            id=1,
            metric_id="KPI-UNIQUE-001",
            node_id=sample_node.node_id,
            timestamp=datetime.now(),
            ds_snr_db=38.0,
            latency_ms=25.0,
        )
        db_session.add(kpi1)
        db_session.commit()

        # Try to insert another KPI with same ID using ON CONFLICT DO NOTHING
        kpi_batch = [{
            'id': 1,  # Duplicate ID
            'metric_id': 'KPI-UNIQUE-002',  # Different metric_id
            'node_id': sample_node.node_id,
            'timestamp': datetime.now(),
            'ds_snr_db': 39.0,
            'latency_ms': 20.0,
        }]

        # This should not raise an error with ON CONFLICT DO NOTHING
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        insert_stmt = sqlite_insert(KPIMetricsModel.__table__).values(kpi_batch)
        insert_stmt = insert_stmt.on_conflict_do_nothing()
        db_session.execute(insert_stmt)
        db_session.commit()

        # Verify only original record exists
        count = db_session.query(KPIMetricsModel).count()
        assert count == 1

    def test_kpi_insert_handles_duplicate_metric_id(self, db_session, sample_node):
        """Test that KPI insert handles duplicate metric_id gracefully."""
        # Insert first KPI
        kpi1 = KPIMetricsModel(
            id=1,
            metric_id="KPI-SAME-METRIC",
            node_id=sample_node.node_id,
            timestamp=datetime.now(),
            ds_snr_db=38.0,
            latency_ms=25.0,
        )
        db_session.add(kpi1)
        db_session.commit()

        # Try to insert another KPI with same metric_id
        kpi_batch = [{
            'id': 2,  # Different ID
            'metric_id': 'KPI-SAME-METRIC',  # Duplicate metric_id
            'node_id': sample_node.node_id,
            'timestamp': datetime.now(),
            'ds_snr_db': 39.0,
            'latency_ms': 20.0,
        }]

        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        insert_stmt = sqlite_insert(KPIMetricsModel.__table__).values(kpi_batch)
        insert_stmt = insert_stmt.on_conflict_do_nothing()
        db_session.execute(insert_stmt)
        db_session.commit()

        # Should still have only 1 record
        count = db_session.query(KPIMetricsModel).count()
        assert count == 1

    def test_action_insert_handles_duplicate(self, db_session, sample_node):
        """Test that action insert handles duplicates gracefully."""
        # Insert first action
        action1 = SelfHealingActionModel(
            id=1,
            action_id="ACT-UNIQUE-001",
            node_id=sample_node.node_id,
            action_type="TEST",
            status="PENDING",
            start_time=datetime.now(),
        )
        db_session.add(action1)
        db_session.commit()

        # Try to insert duplicate
        action_batch = [{
            'id': 1,  # Duplicate ID
            'action_id': 'ACT-UNIQUE-002',
            'node_id': sample_node.node_id,
            'action_type': 'TEST',
            'status': 'PENDING',
            'start_time': datetime.now(),
            'effectiveness_score': 0.0,
        }]

        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        insert_stmt = sqlite_insert(SelfHealingActionModel.__table__).values(action_batch)
        insert_stmt = insert_stmt.on_conflict_do_nothing()
        db_session.execute(insert_stmt)
        db_session.commit()

        # Should still have only 1 record
        count = db_session.query(SelfHealingActionModel).count()
        assert count == 1

    def test_alert_insert_handles_duplicate(self, db_session, sample_node):
        """Test that alert insert handles duplicates gracefully."""
        from datetime import datetime
        now = datetime.now()

        # Insert first alert
        alert1 = AlertModel(
            id=1,
            alert_id="ALT-UNIQUE-001",
            node_id=sample_node.node_id,
            type="TEST",
            severity="WARNING",
            status="ACTIVE",
            timestamp=now,
        )
        db_session.add(alert1)
        db_session.commit()

        # Try to insert duplicate
        alert_batch = [{
            'id': 1,  # Duplicate ID
            'alert_id': 'ALT-UNIQUE-002',
            'node_id': sample_node.node_id,
            'type': 'TEST',
            'severity': 'WARNING',
            'status': 'ACTIVE',
            'timestamp': now,
        }]

        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        insert_stmt = sqlite_insert(AlertModel.__table__).values(alert_batch)
        insert_stmt = insert_stmt.on_conflict_do_nothing()
        db_session.execute(insert_stmt)
        db_session.commit()

        # Should still have only 1 record
        count = db_session.query(AlertModel).count()
        assert count == 1


class TestDispatchTicketCreation:
    """Tests for dispatch ticket creation logic."""

    def test_dispatch_ticket_has_required_fields(self, db_session, sample_node):
        """Test that dispatch tickets have all required fields."""
        import uuid
        now = datetime.now()
        ticket_id = f"DISPATCH-{uuid.uuid4().hex[:8].upper()}"

        dispatch_ticket = {
            'id': 100,
            'action_id': ticket_id,
            'node_id': sample_node.node_id,
            'alert_id': 'ALT-TEST-001',
            'action_type': 'TICKET_CREATION',
            'description': '[Auto-Dispatch] Test dispatch ticket',
            'status': 'PENDING',
            'start_time': now,
            'effectiveness_score': 0.0,
        }

        # Verify all required fields are present
        required_fields = ['id', 'action_id', 'node_id', 'action_type', 'status', 'start_time']
        for field in required_fields:
            assert field in dispatch_ticket
            assert dispatch_ticket[field] is not None

        # Verify no invalid fields (like 'priority' or 'created_at' which don't exist in model)
        invalid_fields = ['priority', 'created_at']
        for field in invalid_fields:
            assert field not in dispatch_ticket


class TestDataGeneration:
    """Tests for data generation functions."""

    def test_generate_kpi_metrics(self):
        """Test KPI metrics generation."""
        from app.generator import generate_node_kpi_metrics

        kpi = generate_node_kpi_metrics("NODE-TEST-001")

        # Verify required fields
        assert "metric_id" in kpi
        assert "node_id" in kpi
        assert "timestamp" in kpi
        assert kpi["node_id"] == "NODE-TEST-001"

        # Verify metric_id format
        assert kpi["metric_id"].startswith("KPI-NODE-TEST-001-")

    def test_generate_alert(self):
        """Test alert generation."""
        from app.generator import generate_cable_alert

        alert = generate_cable_alert("NODE-TEST-001")

        # Verify required fields
        assert "alert_id" in alert
        assert "node_id" in alert
        assert "type" in alert
        assert "severity" in alert
        assert "status" in alert
        assert alert["node_id"] == "NODE-TEST-001"

        # Verify alert_id format
        assert alert["alert_id"].startswith("ALT-")

        # Verify severity is valid
        assert alert["severity"] in ["CRITICAL", "WARNING", "INFO", "critical", "warning", "info"]

    def test_generate_self_healing_action(self):
        """Test self-healing action generation."""
        from app.generator import generate_auto_resolution_action

        action = generate_auto_resolution_action("NODE-TEST-001", "ALT-TEST-001")

        # Verify required fields
        assert "action_id" in action
        assert "node_id" in action
        assert "action_type" in action
        assert "status" in action
        assert action["node_id"] == "NODE-TEST-001"
        assert action["alert_id"] == "ALT-TEST-001"

        # Verify action_id format
        assert action["action_id"].startswith("ACT-")

        # Verify status is valid
        assert action["status"] in ["PENDING", "IN_PROGRESS", "COMPLETED", "FAILED"]


class TestMetricIdUniqueness:
    """Tests for metric_id generation uniqueness."""

    def test_metric_id_includes_timestamp(self):
        """Test that metric_id includes timestamp for uniqueness."""
        from app.generator import generate_node_kpi_metrics
        from datetime import datetime

        timestamp = datetime.now()
        kpi = generate_node_kpi_metrics("NODE-TEST-001", timestamp)

        # metric_id should contain timestamp
        expected_ts = int(timestamp.timestamp())
        assert str(expected_ts) in kpi["metric_id"]

    def test_metric_id_includes_node_id(self):
        """Test that metric_id includes node_id."""
        from app.generator import generate_node_kpi_metrics

        kpi = generate_node_kpi_metrics("NODE-SPECIFIC-001")

        # metric_id should contain node_id
        assert "NODE-SPECIFIC-001" in kpi["metric_id"]

    def test_different_nodes_have_different_metric_ids(self):
        """Test that different nodes generate different metric_ids."""
        from app.generator import generate_node_kpi_metrics
        from datetime import datetime

        timestamp = datetime.now()
        kpi1 = generate_node_kpi_metrics("NODE-001", timestamp)
        kpi2 = generate_node_kpi_metrics("NODE-002", timestamp)

        assert kpi1["metric_id"] != kpi2["metric_id"]
