"""Pytest configuration and fixtures for backend tests."""
# Point the app's own engine/SessionLocal at a throwaway sqlite DB BEFORE any
# app module is imported. The pcap/edge code uses SessionLocal directly (in
# threads and asyncio.to_thread), so it must resolve to the test DB too.
import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="pcap_test_")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TMPDIR}/test.db")
os.environ.setdefault("EDGE_SIM_SPEED", "0")
os.environ.setdefault("EDGE_POLL_INTERVAL_S", "3600")
os.environ.setdefault("EDGE_STAGING_DIR", f"{_TMPDIR}/edge_staging")
os.environ.setdefault("API_KEY", "dev-api-key-change-me")

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app, get_db
from app.database import Base
from app.database import SessionLocal as AppSessionLocal, engine as app_engine
from app.models import (
    FiberNodeModel,
    KPIMetricsModel,
    AlertModel,
    SelfHealingActionModel,
    SLAConfigModel,
    SLABreachModel,
    NetworkDeviceModel,
    ConfigurationTemplateModel,
    ChangeRequestModel,
)


# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override.

    Temporarily removes the app's startup/shutdown handlers to avoid connecting
    to the real PostgreSQL database during tests.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Save and clear startup/shutdown handlers to avoid PostgreSQL connection
    saved_on_startup = app.router.on_startup[:]
    saved_on_shutdown = app.router.on_shutdown[:]
    app.router.on_startup.clear()
    app.router.on_shutdown.clear()

    try:
        with TestClient(app, headers={"X-API-Key": "dev-api-key-change-me"}) as test_client:
            yield test_client
    finally:
        # Restore handlers
        app.router.on_startup = saved_on_startup
        app.router.on_shutdown = saved_on_shutdown
        app.dependency_overrides.clear()


@pytest.fixture
def sample_node(db_session):
    """Create a sample node for testing."""
    node = FiberNodeModel(
        id=1,
        node_id="TWR-TEST-001",
        status="healthy",
        latitude=40.7128,
        longitude=-74.0060,
        region="Northeast",
        city="New York",
    )
    db_session.add(node)
    db_session.commit()
    return node


@pytest.fixture
def sample_alert(db_session, sample_node):
    """Create a sample alert for testing."""
    from datetime import datetime
    alert = AlertModel(
        id=1,
        alert_id="ALT-TEST-001",
        node_id=sample_node.node_id,
        type="HIGH_LATENCY",
        severity="WARNING",
        status="ACTIVE",
        description="Test alert",
        timestamp=datetime.now(),
    )
    db_session.add(alert)
    db_session.commit()
    return alert


@pytest.fixture
def sample_action(db_session, sample_node, sample_alert):
    """Create a sample action for testing."""
    from datetime import datetime
    action = SelfHealingActionModel(
        id=1,
        action_id="ACT-TEST-001",
        node_id=sample_node.node_id,
        alert_id=sample_alert.alert_id,
        action_type="PARAMETER_OPTIMIZATION",
        status="COMPLETED",
        description="Test action",
        start_time=datetime.now(),
        effectiveness_score=0.85,
    )
    db_session.add(action)
    db_session.commit()
    return action


@pytest.fixture
def sample_kpi(db_session, sample_node):
    """Create a sample KPI metric for testing."""
    from datetime import datetime
    kpi = KPIMetricsModel(
        id=1,
        metric_id="KPI-TEST-001",
        node_id=sample_node.node_id,
        timestamp=datetime.now(),
        ds_snr_db=38.5,
        us_snr_db=28.0,
        latency_ms=25.0,
        downstream_throughput_mbps=150.0,
        upstream_throughput_mbps=20.0,
        active_modems=500,
    )
    db_session.add(kpi)
    db_session.commit()
    return kpi


@pytest.fixture
def sample_sla_config(db_session):
    """Create a sample SLA config for testing."""
    config = SLAConfigModel(
        id=1,
        config_key="default",
        uptime_target_percent=99.9,
        max_latency_ms=50.0,
        min_throughput_mbps=100.0,
        cost_per_outage_minute=1000.0,
        revenue_per_subscriber_per_hour=0.50,
    )
    db_session.add(config)
    db_session.commit()
    return config


@pytest.fixture
def sample_network_device(db_session):
    """Create a sample network device for testing."""
    from datetime import datetime
    device = NetworkDeviceModel(
        device_id="FW-TEST-001",
        device_type="firewall",
        device_role="perimeter",
        hostname="firewall-test-001",
        description="Test firewall",
        headend_id="HE-TEST-01",
        region="Northeast",
        manufacturer="Fortinet",
        hardware_model="FortiGate 600F",
        serial_number="FRT000TEST001",
        firmware_version="7.4.1",
        os_version="FortiOS 7.4",
        management_ip="10.1.0.1",
        interfaces=[{"name": "eth0", "status": "up", "speed_gbps": 10}],
        uplink_speed_gbps=10,
        status="operational",
        last_seen=datetime.utcnow(),
        uptime_seconds=86400,
        running_config={"hostname": "firewall-test-001", "acl_rules": [], "ips_enabled": True},
        startup_config={"hostname": "firewall-test-001", "acl_rules": [], "ips_enabled": True},
        config_hash="abc123",
        compliance_status="compliant",
        cpu_utilization=35.0,
        memory_utilization=45.0,
        temperature_celsius=38.0,
    )
    db_session.add(device)
    db_session.commit()
    return device


@pytest.fixture
def sample_config_template(db_session):
    """Create a sample config template for testing."""
    template = ConfigurationTemplateModel(
        template_id="TMPL-FW-PER-TEST01",
        name="Firewall Perimeter Baseline",
        description="Test template",
        device_type="firewall",
        device_role="perimeter",
        config_template={"hostname": "template", "ips_enabled": True},
        version="1.0",
        is_active=True,
        created_by="test",
    )
    db_session.add(template)
    db_session.commit()
    return template


@pytest.fixture
def sample_change_request(db_session, sample_network_device):
    """Create a sample change request for testing."""
    cr = ChangeRequestModel(
        request_id="CR-TEST-001",
        title="Test change request",
        description="Update firewall ACLs",
        change_type="security",
        target_devices=[{"device_id": sample_network_device.device_id,
                         "device_type": "firewall", "hostname": "firewall-test-001"}],
        device_count=1,
        status="pending_review",
        requested_by="test_user",
    )
    db_session.add(cr)
    db_session.commit()
    return cr


# ===========================================================================
# Fixtures for the packet-capture + edge anomaly flow
# ===========================================================================
# These use the app's OWN engine/SessionLocal (sqlite test DB set at top of
# this file), because the pcap/edge modules open SessionLocal directly rather
# than going through the get_db dependency.

from app.models import HeadendModel  # noqa: E402
from app.pcap.schemas import AgentResponse, Finding, PcapMetadata  # noqa: E402


@pytest.fixture(scope="function")
def pcap_db():
    """Fresh app-DB schema per test; seed one headend the edge flow can target."""
    Base.metadata.create_all(bind=app_engine)
    db = AppSessionLocal()
    try:
        db.add(HeadendModel(
            id=1, headend_id="HE-TEST-01", name="Denver Headend",
            region="West", city="Denver", state="CO",
            latitude=39.7392, longitude=-104.9903,
        ))
        db.commit()
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=app_engine)


@pytest.fixture(scope="function")
def pcap_client(pcap_db):
    """TestClient wired to the app engine (same DB the pcap/edge code uses)."""
    def _override_get_db():
        db = AppSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    saved_startup = app.router.on_startup[:]
    saved_shutdown = app.router.on_shutdown[:]
    app.router.on_startup.clear()
    app.router.on_shutdown.clear()
    try:
        with TestClient(app, headers={"X-API-Key": "dev-api-key-change-me"}) as c:
            yield c
    finally:
        app.router.on_startup = saved_startup
        app.router.on_shutdown = saved_shutdown
        app.dependency_overrides.clear()


@pytest.fixture
def anon_pcap_client(pcap_db):
    """Same as pcap_client but without the API key header."""
    def _override_get_db():
        db = AppSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    saved_startup = app.router.on_startup[:]
    saved_shutdown = app.router.on_shutdown[:]
    app.router.on_startup.clear()
    app.router.on_shutdown.clear()
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.router.on_startup = saved_startup
        app.router.on_shutdown = saved_shutdown
        app.dependency_overrides.clear()


@pytest.fixture
def sample_pcap_metadata() -> PcapMetadata:
    return PcapMetadata(
        total_packets=123,
        time_range_start="2026-08-11T10:00:00",
        time_range_end="2026-08-11T10:05:00",
        protocols={"TCP": 100, "UDP": 23},
        top_connections=[],
        payload_findings=[],
        http_requests=[],
        unique_src_ips=4,
        unique_dst_ips=7,
    )


@pytest.fixture
def sample_pcap_agents() -> list:
    return [
        AgentResponse(
            agent_name="Threat Detection Agent",
            severity="high",
            analysis="Suspicious beaconing observed.",
            findings=[Finding(type="c2_beacon", description="Periodic outbound", risk="high")],
            recommendations=["Block the destination IP"],
        )
    ]


@pytest.fixture(autouse=True)
def _mock_pcap_network(monkeypatch):
    """Keep pcap parsing/enrichment hermetic — no ip-api/ThreatFox/NVD calls."""
    async def _no_enrich(meta, **kw):
        return {}, []
    monkeypatch.setattr("app.pcap.geoip.lookup", lambda ips: {}, raising=False)
    monkeypatch.setattr("app.pcap.threat_intel.enrich", _no_enrich, raising=False)
    yield


# Canned analyst JSON (no IPs cited, so anti-fabrication validators keep it).
CANNED_LLM_JSON = (
    '{"severity":"high","analysis":"## Summary\\nScan behaviour detected.",'
    '"findings":[{"type":"scan","description":"port fan-out observed",'
    '"evidence":["many destination ports"],"risk":"medium"}],'
    '"recommendations":["Quarantine the source host"]}'
)
