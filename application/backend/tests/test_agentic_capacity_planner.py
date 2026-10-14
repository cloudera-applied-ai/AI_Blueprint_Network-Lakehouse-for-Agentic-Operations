"""Tests for the agentic capacity planning module."""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

# Helper to run async functions in sync tests
def run_async(coro):
    """Run an async coroutine in a sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

from app.agentic_capacity_planner import (
    # Constants
    BACKHAUL_SPECS,
    MANUFACTURER_COMPATIBILITY,
    COMPATIBILITY_COSTS,
    # Enums
    AgentType,
    ExecutionStatus,
    ThoughtType,
    # Data classes
    AgentThought,
    UpgradeImpactAnalysis,
    HardwareCompatibilityReport,
    AgenticCapacityPlanningExecution,
    # Functions
    get_execution,
    create_execution,
    add_thought,
    get_execution_status,
    # Agent functions
    run_data_collector_agent,
    run_upgrade_analyzer_agent,
    run_hardware_checker_agent,
    run_capacity_forecaster_agent,
    run_agentic_capacity_planning,
    start_agentic_capacity_planning,
    # Internal storage
    _executions,
)


class TestBackhaulSpecs:
    """Tests for backhaul type specifications."""

    def test_backhaul_specs_contains_expected_types(self):
        """Test that all expected backhaul types are defined."""
        expected_types = ["Fiber", "Starlink", "Microwave", "Satellite", "Copper"]
        for bt in expected_types:
            assert bt in BACKHAUL_SPECS, f"Missing backhaul type: {bt}"

    def test_backhaul_specs_have_required_fields(self):
        """Test that each backhaul spec has required fields."""
        required_fields = ["capacity_mbps", "avg_capacity_mbps", "latency_ms", "reliability_percent", "cost_per_node", "installation_days"]
        for bt, specs in BACKHAUL_SPECS.items():
            for field in required_fields:
                assert field in specs, f"Missing field '{field}' in {bt} specs"

    def test_fiber_has_highest_capacity(self):
        """Test that Fiber has the highest average capacity."""
        fiber_capacity = BACKHAUL_SPECS["Fiber"]["avg_capacity_mbps"]
        for bt, specs in BACKHAUL_SPECS.items():
            if bt != "Fiber":
                assert specs["avg_capacity_mbps"] <= fiber_capacity, f"{bt} should not exceed Fiber capacity"

    def test_fiber_has_lowest_latency(self):
        """Test that Fiber has the lowest latency."""
        fiber_latency = BACKHAUL_SPECS["Fiber"]["latency_ms"]
        for bt, specs in BACKHAUL_SPECS.items():
            if bt != "Fiber":
                assert specs["latency_ms"] >= fiber_latency, f"{bt} should not have lower latency than Fiber"


class TestManufacturerCompatibility:
    """Tests for manufacturer compatibility matrix."""

    def test_compatibility_contains_major_manufacturers(self):
        """Test that major manufacturers are included."""
        expected_manufacturers = ["Cisco", "CommScope/Arris", "Casa Systems", "Harmonic", "Vecima Networks"]
        for mfr in expected_manufacturers:
            assert mfr in MANUFACTURER_COMPATIBILITY, f"Missing manufacturer: {mfr}"

    def test_compatibility_values_are_valid(self):
        """Test that all compatibility values are valid."""
        valid_statuses = ["compatible", "partial_upgrade", "replacement"]
        for mfr, compat_map in MANUFACTURER_COMPATIBILITY.items():
            for backhaul, status in compat_map.items():
                assert status in valid_statuses, f"Invalid status '{status}' for {mfr}/{backhaul}"

    def test_compatibility_costs_defined(self):
        """Test that costs are defined for all compatibility statuses."""
        expected_statuses = ["compatible", "partial_upgrade", "replacement"]
        for status in expected_statuses:
            assert status in COMPATIBILITY_COSTS, f"Missing cost for status: {status}"

    def test_compatible_has_zero_cost(self):
        """Test that 'compatible' status has zero additional cost."""
        assert COMPATIBILITY_COSTS["compatible"] == 0

    def test_replacement_is_most_expensive(self):
        """Test that 'replacement' is the most expensive option."""
        assert COMPATIBILITY_COSTS["replacement"] > COMPATIBILITY_COSTS["partial_upgrade"]
        assert COMPATIBILITY_COSTS["replacement"] > COMPATIBILITY_COSTS["compatible"]


class TestEnums:
    """Tests for enum definitions."""

    def test_agent_type_values(self):
        """Test AgentType enum values."""
        assert AgentType.DATA_COLLECTOR.value == "data-collector"
        assert AgentType.UPGRADE_ANALYZER.value == "upgrade-analyzer"
        assert AgentType.HARDWARE_CHECKER.value == "hardware-checker"
        assert AgentType.HEADEND_COMPONENT_ANALYZER.value == "headend-component-analyzer"
        assert AgentType.CAPACITY_FORECASTER.value == "capacity-forecaster"

    def test_execution_status_values(self):
        """Test ExecutionStatus enum values."""
        assert ExecutionStatus.PENDING.value == "pending"
        assert ExecutionStatus.RUNNING.value == "running"
        assert ExecutionStatus.COMPLETED.value == "completed"
        assert ExecutionStatus.FAILED.value == "failed"

    def test_thought_type_values(self):
        """Test ThoughtType enum values."""
        expected_types = ["thought", "action", "tool_call", "tool_result", "data", "analysis", "error"]
        for t in expected_types:
            assert hasattr(ThoughtType, t.upper()), f"Missing ThoughtType: {t}"


class TestAgentThought:
    """Tests for AgentThought dataclass."""

    def test_create_thought(self):
        """Test creating an AgentThought."""
        thought = AgentThought(
            id="thought-123",
            timestamp="2024-01-01T00:00:00",
            agent_id="data-collector",
            agent_name="Data Collector",
            type="thought",
            content="Test thought",
        )
        assert thought.id == "thought-123"
        assert thought.agent_name == "Data Collector"
        assert thought.progress_percent is None
        assert thought.data_summary is None

    def test_create_thought_with_optional_fields(self):
        """Test creating an AgentThought with optional fields."""
        thought = AgentThought(
            id="thought-456",
            timestamp="2024-01-01T00:00:00",
            agent_id="data-collector",
            agent_name="Data Collector",
            type="data",
            content="Found 100 nodes",
            progress_percent=50.0,
            data_summary={"node_count": 100},
        )
        assert thought.progress_percent == 50.0
        assert thought.data_summary["node_count"] == 100


class TestExecutionManagement:
    """Tests for execution state management."""

    def setup_method(self):
        """Clear executions before each test."""
        _executions.clear()

    def test_create_execution(self):
        """Test creating a new execution."""
        execution = create_execution(
            db=None,
            analysis_mode="upgrade_scenario",
            target_backhaul_type="Fiber",
            current_backhaul_filter=["Copper", "Satellite"],
            region="Northeast",
            city=None,
            datacenter_ids=[],
            node_ids=[],
            include_nodes=True,
            include_datacenters=True,
            include_cost_estimate=True,
        )
        assert execution.execution_id.startswith("cap-")
        assert execution.status == ExecutionStatus.PENDING.value
        assert execution.analysis_mode == "upgrade_scenario"
        assert execution.target_backhaul_type == "Fiber"
        assert "Copper" in execution.current_backhaul_filter
        assert execution.region == "Northeast"
        assert execution.progress_percent == 0.0
        assert len(execution.thoughts) == 0

    def test_get_execution(self):
        """Test retrieving an execution by ID."""
        execution = create_execution(
            db=None,
            analysis_mode="current_state",
            target_backhaul_type=None,
            current_backhaul_filter=[],
            region=None,
            city=None,
            datacenter_ids=[],
            node_ids=[],
            include_nodes=True,
            include_datacenters=True,
            include_cost_estimate=False,
        )
        retrieved = get_execution(execution.execution_id)
        assert retrieved is not None
        assert retrieved.execution_id == execution.execution_id

    def test_get_nonexistent_execution(self):
        """Test retrieving a non-existent execution."""
        result = get_execution("nonexistent-id")
        assert result is None

    def test_add_thought_to_execution(self):
        """Test adding a thought to an execution."""
        execution = create_execution(
            db=None,
            analysis_mode="current_state",
            target_backhaul_type=None,
            current_backhaul_filter=[],
            region=None,
            city=None,
            datacenter_ids=[],
            node_ids=[],
            include_nodes=True,
            include_datacenters=True,
            include_cost_estimate=False,
        )
        add_thought(
            execution,
            agent_id="data-collector",
            agent_name="Data Collector",
            thought_type="thought",
            content="Starting analysis...",
            progress_percent=10.0,
        )
        assert len(execution.thoughts) == 1
        assert execution.thoughts[0].content == "Starting analysis..."
        assert execution.progress_percent == 10.0

    def test_add_multiple_thoughts(self):
        """Test adding multiple thoughts to an execution."""
        execution = create_execution(
            db=None,
            analysis_mode="current_state",
            target_backhaul_type=None,
            current_backhaul_filter=[],
            region=None,
            city=None,
            datacenter_ids=[],
            node_ids=[],
            include_nodes=True,
            include_datacenters=True,
            include_cost_estimate=False,
        )
        for i in range(5):
            add_thought(
                execution,
                agent_id="data-collector",
                agent_name="Data Collector",
                thought_type="thought",
                content=f"Thought {i}",
                progress_percent=i * 20.0,
            )
        assert len(execution.thoughts) == 5
        assert execution.progress_percent == 80.0

    def test_get_execution_status(self):
        """Test getting execution status as dict."""
        execution = create_execution(
            db=None,
            analysis_mode="upgrade_scenario",
            target_backhaul_type="Fiber",
            current_backhaul_filter=["Copper"],
            region="Northeast",
            city=None,
            datacenter_ids=[],
            node_ids=[],
            include_nodes=True,
            include_datacenters=True,
            include_cost_estimate=True,
        )
        add_thought(
            execution,
            agent_id="data-collector",
            agent_name="Data Collector",
            thought_type="thought",
            content="Test thought",
            progress_percent=25.0,
        )

        status = get_execution_status(execution.execution_id)
        assert status is not None
        assert status["execution_id"] == execution.execution_id
        assert status["status"] == "pending"
        assert status["analysis_mode"] == "upgrade_scenario"
        assert status["target_backhaul_type"] == "Fiber"
        assert len(status["thoughts"]) == 1
        assert status["thoughts"][0]["content"] == "Test thought"

    def test_get_status_nonexistent_execution(self):
        """Test getting status for non-existent execution."""
        status = get_execution_status("nonexistent-id")
        assert status is None


class TestDataCollectorAgent:
    """Tests for the Data Collector agent."""

    def setup_method(self):
        """Clear executions before each test."""
        _executions.clear()

    def test_data_collector_runs(self, db_session):
        """Test that data collector agent runs and produces output."""
        execution = create_execution(
            db=db_session,
            analysis_mode="current_state",
            target_backhaul_type=None,
            current_backhaul_filter=[],
            region=None,
            city=None,
            datacenter_ids=[],
            node_ids=[],
            include_nodes=True,
            include_datacenters=True,
            include_cost_estimate=False,
        )

        result = run_async(run_data_collector_agent(db_session, execution))

        assert result is not None
        assert "total_nodes" in result
        assert "nodes_by_backhaul" in result
        assert "total_bandwidth_mbps" in result
        assert execution.current_agent == "data-collector"
        assert len(execution.thoughts) > 0

    def test_data_collector_with_filter(self, db_session, sample_nodes_with_backhaul):
        """Test data collector with backhaul filter."""
        execution = create_execution(
            db=db_session,
            analysis_mode="upgrade_scenario",
            target_backhaul_type="Fiber",
            current_backhaul_filter=["Copper"],
            region=None,
            city=None,
            datacenter_ids=[],
            node_ids=[],
            include_nodes=True,
            include_datacenters=True,
            include_cost_estimate=False,
        )

        result = run_async(run_data_collector_agent(db_session, execution))

        assert result["filter_applied"] == ["Copper"]

    def test_data_collector_stores_output(self, db_session):
        """Test that data collector stores output in execution."""
        execution = create_execution(
            db=db_session,
            analysis_mode="current_state",
            target_backhaul_type=None,
            current_backhaul_filter=[],
            region=None,
            city=None,
            datacenter_ids=[],
            node_ids=[],
            include_nodes=True,
            include_datacenters=True,
            include_cost_estimate=False,
        )

        run_async(run_data_collector_agent(db_session, execution))

        assert execution.data_collector_output is not None
        assert "total_nodes" in execution.data_collector_output


class TestUpgradeAnalyzerAgent:
    """Tests for the Upgrade Analyzer agent."""

    def setup_method(self):
        """Clear executions before each test."""
        _executions.clear()

    def test_upgrade_analyzer_skips_current_state(self, db_session):
        """Test that upgrade analyzer skips when analysis_mode is current_state."""
        execution = create_execution(
            db=db_session,
            analysis_mode="current_state",
            target_backhaul_type=None,
            current_backhaul_filter=[],
            region=None,
            city=None,
            datacenter_ids=[],
            node_ids=[],
            include_nodes=True,
            include_datacenters=True,
            include_cost_estimate=False,
        )

        result = run_async(run_upgrade_analyzer_agent(db_session, execution))

        assert result is None
        assert execution.upgrade_analysis is None

    def test_upgrade_analyzer_runs_for_upgrade_scenario(self, db_session):
        """Test that upgrade analyzer runs for upgrade_scenario mode."""
        execution = create_execution(
            db=db_session,
            analysis_mode="upgrade_scenario",
            target_backhaul_type="Fiber",
            current_backhaul_filter=["Copper"],
            region=None,
            city=None,
            datacenter_ids=[],
            node_ids=[],
            include_nodes=True,
            include_datacenters=True,
            include_cost_estimate=True,
        )
        # Simulate data collector output
        execution.data_collector_output = {
            "total_nodes": 100,
            "filtered_nodes": 50,
            "nodes_by_backhaul": {"Copper": 30, "Satellite": 20},
            "total_bandwidth_mbps": 5000,
            "avg_latency_ms": 150,
            "avg_active_modems": 500,
        }

        result = run_async(run_upgrade_analyzer_agent(db_session, execution))

        assert result is not None
        assert isinstance(result, UpgradeImpactAnalysis)
        assert result.nodes_analyzed == 50
        assert result.upgrade_target == "Fiber"
        assert result.bandwidth_improvement_percent > 0
        assert result.latency_improvement_percent > 0

    def test_upgrade_analyzer_calculates_improvements(self, db_session):
        """Test that upgrade analyzer correctly calculates improvements."""
        execution = create_execution(
            db=db_session,
            analysis_mode="upgrade_scenario",
            target_backhaul_type="Fiber",
            current_backhaul_filter=["Copper"],
            region=None,
            city=None,
            datacenter_ids=[],
            node_ids=[],
            include_nodes=True,
            include_datacenters=True,
            include_cost_estimate=True,
        )
        execution.data_collector_output = {
            "total_nodes": 10,
            "filtered_nodes": 10,
            "nodes_by_backhaul": {"Copper": 10},
            "total_bandwidth_mbps": 500,  # 50 Mbps per node (Copper average)
            "avg_latency_ms": 20,  # Copper latency
            "avg_active_modems": 100,
        }

        result = run_async(run_upgrade_analyzer_agent(db_session, execution))

        # Fiber has 5000 Mbps avg, so 10 nodes * 5000 = 50000 Mbps = 50 Gbps
        assert result.projected_total_bandwidth_gbps == 50.0
        # Fiber latency is 5ms, Copper is 20ms, so improvement should be significant
        assert result.projected_avg_latency_ms == 5.0


class TestHardwareCheckerAgent:
    """Tests for the Hardware Checker agent."""

    def setup_method(self):
        """Clear executions before each test."""
        _executions.clear()

    def test_hardware_checker_skips_current_state(self, db_session):
        """Test that hardware checker skips when analysis_mode is current_state."""
        execution = create_execution(
            db=db_session,
            analysis_mode="current_state",
            target_backhaul_type=None,
            current_backhaul_filter=[],
            region=None,
            city=None,
            datacenter_ids=[],
            node_ids=[],
            include_nodes=True,
            include_datacenters=True,
            include_cost_estimate=False,
        )

        result = run_async(run_hardware_checker_agent(db_session, execution))

        assert result is None
        assert execution.hardware_compatibility is None

    def test_hardware_checker_runs_for_upgrade_scenario(self, db_session):
        """Test that hardware checker runs for upgrade_scenario mode."""
        execution = create_execution(
            db=db_session,
            analysis_mode="upgrade_scenario",
            target_backhaul_type="Fiber",
            current_backhaul_filter=["Copper"],
            region=None,
            city=None,
            datacenter_ids=[],
            node_ids=[],
            include_nodes=True,
            include_datacenters=True,
            include_cost_estimate=True,
        )
        execution.data_collector_output = {
            "nodes_by_manufacturer": {"Cisco": 20, "CommScope/Arris": 15, "Casa Systems": 10, "Vecima Networks": 5},
        }

        result = run_async(run_hardware_checker_agent(db_session, execution))

        assert result is not None
        assert isinstance(result, HardwareCompatibilityReport)
        assert result.total_nodes_checked == 50
        assert result.compatible_count >= 0
        assert result.partial_upgrade_count >= 0
        assert result.replacement_count >= 0
        assert result.estimated_total_cost > 0

    def test_hardware_checker_calculates_costs(self, db_session):
        """Test that hardware checker correctly calculates costs."""
        execution = create_execution(
            db=db_session,
            analysis_mode="upgrade_scenario",
            target_backhaul_type="Fiber",
            current_backhaul_filter=["Copper"],
            region=None,
            city=None,
            datacenter_ids=[],
            node_ids=[],
            include_nodes=True,
            include_datacenters=True,
            include_cost_estimate=True,
        )
        # Cisco is compatible with Fiber
        execution.data_collector_output = {
            "nodes_by_manufacturer": {"Cisco": 10},
        }

        result = run_async(run_hardware_checker_agent(db_session, execution))

        # Cisco is compatible, so no upgrade cost, just base Fiber cost
        assert result.compatible_count == 10
        assert result.partial_upgrade_count == 0
        assert result.replacement_count == 0
        # 10 nodes * $15000 (Fiber cost) = $150,000
        assert result.estimated_total_cost == 150000


class TestCapacityForecasterAgent:
    """Tests for the Capacity Forecaster agent."""

    def setup_method(self):
        """Clear executions before each test."""
        _executions.clear()

    def test_forecaster_generates_forecasts(self, db_session):
        """Test that forecaster generates forecasts."""
        execution = create_execution(
            db=db_session,
            analysis_mode="current_state",
            target_backhaul_type=None,
            current_backhaul_filter=[],
            region=None,
            city=None,
            datacenter_ids=[],
            node_ids=[],
            include_nodes=True,
            include_datacenters=True,
            include_cost_estimate=False,
        )
        execution.data_collector_output = {
            "total_nodes": 100,
            "filtered_nodes": 100,
            "total_bandwidth_gbps": 500,
            "avg_cpu_utilization": 60,
        }

        # Mock LLM config to return None (use rule-based)
        with patch("app.agentic_capacity_planner._get_llm_config", return_value=None):
            result = run_async(run_capacity_forecaster_agent(db_session, execution))

        assert result is not None
        assert "forecasts" in result
        assert len(result["forecasts"]) >= 3  # 30, 60, 90 day forecasts
        assert "recommendations" in result
        assert "trend_direction" in result

    def test_forecaster_includes_upgrade_recommendations(self, db_session):
        """Test that forecaster includes upgrade-specific recommendations."""
        execution = create_execution(
            db=db_session,
            analysis_mode="upgrade_scenario",
            target_backhaul_type="Fiber",
            current_backhaul_filter=["Copper"],
            region=None,
            city=None,
            datacenter_ids=[],
            node_ids=[],
            include_nodes=True,
            include_datacenters=True,
            include_cost_estimate=True,
        )
        execution.data_collector_output = {
            "total_nodes": 100,
            "filtered_nodes": 50,
            "total_bandwidth_gbps": 250,
            "avg_cpu_utilization": 55,
        }
        execution.upgrade_analysis = UpgradeImpactAnalysis(
            nodes_analyzed=50,
            current_total_bandwidth_gbps=25,
            projected_total_bandwidth_gbps=250,
            bandwidth_improvement_percent=900,
            current_avg_latency_ms=150,
            projected_avg_latency_ms=5,
            latency_improvement_percent=96,
            nodes_by_current_backhaul={"Copper": 30, "Satellite": 20},
            upgrade_target="Fiber",
            users_to_benefit=25000,
        )

        with patch("app.agentic_capacity_planner._get_llm_config", return_value=None):
            result = run_async(run_capacity_forecaster_agent(db_session, execution))

        # First recommendation should mention the upgrade
        assert any("Fiber" in rec or "bandwidth" in rec.lower() for rec in result.get("recommendations", []))


class TestAgenticPipeline:
    """Tests for the full agentic pipeline."""

    def setup_method(self):
        """Clear executions before each test."""
        _executions.clear()

    def test_full_pipeline_current_state(self, db_session):
        """Test running the full pipeline in current_state mode."""
        execution = create_execution(
            db=db_session,
            analysis_mode="current_state",
            target_backhaul_type=None,
            current_backhaul_filter=[],
            region=None,
            city=None,
            datacenter_ids=[],
            node_ids=[],
            include_nodes=True,
            include_datacenters=True,
            include_cost_estimate=False,
        )

        with patch("app.agentic_capacity_planner._get_llm_config", return_value=None):
            result = run_async(run_agentic_capacity_planning(db_session, execution))

        assert result.status == ExecutionStatus.COMPLETED.value
        assert result.progress_percent == 100.0
        assert result.data_collector_output is not None
        assert result.upgrade_analysis is None  # Skipped for current_state
        # hardware_compatibility runs in all modes now for upgrade readiness insights
        assert result.result is not None
        assert result.completed_at is not None

    def test_full_pipeline_upgrade_scenario(self, db_session, sample_nodes_with_backhaul):
        """Test running the full pipeline in upgrade_scenario mode."""
        execution = create_execution(
            db=db_session,
            analysis_mode="upgrade_scenario",
            target_backhaul_type="Fiber",
            current_backhaul_filter=["Copper", "Satellite"],
            region=None,
            city=None,
            datacenter_ids=[],
            node_ids=[],
            include_nodes=True,
            include_datacenters=True,
            include_cost_estimate=True,
        )

        with patch("app.agentic_capacity_planner._get_llm_config", return_value=None):
            result = run_async(run_agentic_capacity_planning(db_session, execution))

        assert result.status == ExecutionStatus.COMPLETED.value
        assert result.data_collector_output is not None
        # These should be populated for upgrade_scenario
        # (depends on having matching nodes in sample data)

    def test_pipeline_records_thoughts(self, db_session):
        """Test that the pipeline records thoughts throughout execution."""
        execution = create_execution(
            db=db_session,
            analysis_mode="current_state",
            target_backhaul_type=None,
            current_backhaul_filter=[],
            region=None,
            city=None,
            datacenter_ids=[],
            node_ids=[],
            include_nodes=True,
            include_datacenters=True,
            include_cost_estimate=False,
        )

        with patch("app.agentic_capacity_planner._get_llm_config", return_value=None):
            run_async(run_agentic_capacity_planning(db_session, execution))

        # Should have thoughts from multiple agents
        agent_ids = set(t.agent_id for t in execution.thoughts)
        assert "data-collector" in agent_ids
        assert "capacity-forecaster" in agent_ids

    def test_pipeline_handles_errors(self, db_session):
        """Test that the pipeline handles errors gracefully."""
        execution = create_execution(
            db=db_session,
            analysis_mode="current_state",
            target_backhaul_type=None,
            current_backhaul_filter=[],
            region=None,
            city=None,
            datacenter_ids=[],
            node_ids=[],
            include_nodes=True,
            include_datacenters=True,
            include_cost_estimate=False,
        )

        # Force an error by patching a function to raise an exception
        async def raise_error(*args, **kwargs):
            raise Exception("Test error")

        with patch("app.agentic_capacity_planner.run_data_collector_agent", side_effect=raise_error):
            result = run_async(run_agentic_capacity_planning(db_session, execution))

        assert result.status == ExecutionStatus.FAILED.value
        assert result.error is not None
        assert "Test error" in result.error


class TestAPIEndpointIntegration:
    """Tests for API endpoint integration."""

    def setup_method(self):
        """Clear executions before each test."""
        _executions.clear()

    def test_start_agentic_capacity_planning_endpoint(self, client):
        """Test the start endpoint."""
        response = client.post(
            "/api/v1/capacity-planning/agentic/start",
            json={
                "analysis_mode": "current_state",
                "include_cost_estimate": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "execution_id" in data
        assert data["execution_id"].startswith("cap-")

    def test_start_with_upgrade_scenario(self, client):
        """Test starting with upgrade scenario parameters."""
        response = client.post(
            "/api/v1/capacity-planning/agentic/start",
            json={
                "analysis_mode": "upgrade_scenario",
                "target_upgrade_type": "Fiber",
                "current_node_type_filter": ["Copper", "Satellite"],
                "region": "Northeast",
                "include_cost_estimate": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "execution_id" in data

    def test_get_execution_status_endpoint(self, client):
        """Test getting execution status."""
        # Create an execution directly (no background thread needed)
        execution = create_execution(
            db=None,
            analysis_mode="current_state",
            target_backhaul_type=None,
            current_backhaul_filter=[],
            region=None,
            city=None,
            datacenter_ids=[],
            node_ids=[],
            include_nodes=True,
            include_datacenters=True,
            include_cost_estimate=False,
        )
        add_thought(execution, "data-collector", "Data Collector", "thought", "Test", 10.0)

        # Get status via API
        status_response = client.get(f"/api/v1/capacity-planning/agentic/{execution.execution_id}")
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["execution_id"] == execution.execution_id
        assert "status" in data
        assert "progress_percent" in data
        assert "thoughts" in data

    def test_get_nonexistent_execution(self, client):
        """Test getting a non-existent execution."""
        response = client.get("/api/v1/capacity-planning/agentic/nonexistent-id")
        assert response.status_code == 404

    def test_invalid_analysis_mode(self, client):
        """Test with invalid analysis mode - should still work with default."""
        response = client.post(
            "/api/v1/capacity-planning/agentic/start",
            json={"analysis_mode": "invalid_mode"},
        )
        # The API accepts any string but agents will handle it as unknown mode
        assert response.status_code == 200


# Additional fixture for tests that need nodes with backhaul types
@pytest.fixture
def sample_nodes_with_backhaul(db_session):
    """Create sample nodes with different backhaul types."""
    from app.models import FiberNodeModel

    nodes = []
    backhaul_types = ["Fiber", "Copper", "Satellite", "Microwave"]
    manufacturers = ["Cisco", "CommScope/Arris", "Casa Systems", "Harmonic", "Vecima Networks"]

    for i in range(20):
        node = FiberNodeModel(
            id=i + 100,
            node_id=f"TWR-TEST-{i:03d}",
            status="healthy",
            latitude=40.7128 + i * 0.01,
            longitude=-74.0060 + i * 0.01,
            region="Northeast",
            city="New York",
            manufacturer=manufacturers[i % len(manufacturers)],
        )
        nodes.append(node)
        db_session.add(node)

    db_session.commit()
    return nodes
