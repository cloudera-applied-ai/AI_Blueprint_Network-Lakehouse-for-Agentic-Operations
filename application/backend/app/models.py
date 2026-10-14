"""SQLAlchemy database models for Cable Network ISP Data Lakehouse"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, Index
from sqlalchemy.sql import func
from .database import Base


# ============================================
# Cable Plant Infrastructure Models
# ============================================

class FiberNodeModel(Base):
    """Fiber Node - Primary HFC plant element"""
    __tablename__ = "fiber_nodes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    node_id = Column(String, unique=True, index=True, nullable=False)
    headend_id = Column(String, index=True)
    hub_id = Column(String, index=True)
    service_area = Column(String, index=True)
    region = Column(String, index=True)
    city = Column(String)
    state = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)

    # Node classification
    node_type = Column(String, index=True)  # N+0, N+1, N+2, N+3
    homes_passed = Column(Integer)
    homes_active = Column(Integer)
    docsis_version = Column(String)  # 3.0, 3.1, 4.0

    # RF Configuration
    downstream_channels = Column(Integer)
    upstream_channels = Column(Integer)
    ofdm_channels = Column(Integer)
    ofdma_channels = Column(Integer)

    # Equipment
    manufacturer = Column(String, index=True)
    hardware_model = Column(String)
    firmware_version = Column(String)

    # Power
    power_supply_count = Column(Integer)
    power_supply_status = Column(String)  # all_ok, partial_failure, critical
    battery_backup_hours = Column(Float)

    # Plant details
    amplifier_cascade = Column(Integer)  # Number of amplifiers in cascade
    coax_plant_miles = Column(Float)
    fiber_miles = Column(Float)
    tap_count = Column(Integer)

    # Status
    status = Column(String, index=True)  # operational, degraded, failed, maintenance
    upstream_cmts_id = Column(String, index=True)
    neighbor_nodes = Column(JSON)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class HeadendModel(Base):
    """Headend - Central facility housing CMTS equipment (replaces DataCenter)"""
    __tablename__ = "headends"

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    headend_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    region = Column(String, index=True)
    service_area = Column(String, index=True)
    city = Column(String)
    state = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)

    # Infrastructure
    cmts_count = Column(Integer)
    total_cmts_ports = Column(Integer)
    active_cmts_ports = Column(Integer)
    video_server_count = Column(Integer)
    core_router_count = Column(Integer)
    peering_capacity_gbps = Column(Float)
    total_rack_units = Column(Integer)
    power_capacity_mw = Column(Float)

    # Subscribers
    total_homes_served = Column(Integer)
    total_active_subscribers = Column(Integer)

    # Status
    status = Column(String, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class CMTSModel(Base):
    """Cable Modem Termination System"""
    __tablename__ = "cmts_devices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    cmts_id = Column(String, unique=True, index=True, nullable=False)
    headend_id = Column(String, index=True, nullable=False)
    manufacturer = Column(String, index=True)  # Cisco, Casa, Harmonic
    model = Column(String)  # cBR-8, C100G, CableOS
    firmware_version = Column(String)

    # Port capacity
    total_ds_ports = Column(Integer)
    total_us_ports = Column(Integer)

    # Modem stats
    active_modems = Column(Integer)
    registered_modems = Column(Integer)
    offline_modems = Column(Integer)
    max_modems_capacity = Column(Integer)

    # Utilization
    avg_ds_utilization = Column(Float)
    avg_us_utilization = Column(Float)
    ranging_success_rate = Column(Float)
    t3_timeouts_24h = Column(Integer)
    t4_timeouts_24h = Column(Integer)

    # Hardware
    cpu_utilization = Column(Float)
    memory_utilization = Column(Float)
    temperature_celsius = Column(Float)
    uplink_capacity_gbps = Column(Float)

    status = Column(String, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class HubModel(Base):
    """Hub site - Intermediate facility between headend and nodes"""
    __tablename__ = "hubs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    hub_id = Column(String, unique=True, index=True, nullable=False)
    headend_id = Column(String, index=True, nullable=False)
    name = Column(String)
    city = Column(String)
    state = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)

    # Capacity
    fiber_nodes_served = Column(Integer)
    total_homes_served = Column(Integer)
    fiber_capacity_gbps = Column(Float)
    current_throughput_gbps = Column(Float)

    # Power & status
    power_status = Column(String)  # normal, battery, generator
    battery_backup_hours = Column(Float)
    status = Column(String, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AmplifierModel(Base):
    """RF Amplifier in HFC plant"""
    __tablename__ = "amplifiers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    amp_id = Column(String, unique=True, index=True, nullable=False)
    node_id = Column(String, index=True, nullable=False)
    manufacturer = Column(String)
    model = Column(String)

    # Classification
    amp_type = Column(String, index=True)  # trunk, bridger, line_extender, distribution
    cascade_position = Column(Integer)
    location_type = Column(String)  # aerial, pedestal, underground

    # RF levels (dBmV)
    ds_input_level = Column(Float)
    ds_output_level = Column(Float)
    us_input_level = Column(Float)
    us_output_level = Column(Float)

    # Signal quality
    ds_snr = Column(Float)
    us_snr = Column(Float)

    # Equipment status
    temperature_celsius = Column(Float)
    power_consumption_watts = Column(Float)
    power_supply_status = Column(String)  # normal, degraded, failed
    status = Column(String, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ============================================
# Customer / Subscriber Models
# ============================================

class CustomerAccountModel(Base):
    """Customer account with service and CPE details"""
    __tablename__ = "customer_accounts"

    __table_args__ = (
        Index('idx_customer_node', 'node_id'),
        Index('idx_customer_status', 'account_status'),
        Index('idx_customer_plan', 'service_plan'),
        Index('idx_customer_node_status', 'node_id', 'account_status'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    account_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)

    # Plant connection
    node_id = Column(String, index=True, nullable=False)
    tap_id = Column(String)
    drop_length_ft = Column(Float)
    drop_quality = Column(String)  # good, fair, poor

    # Service plan
    service_plan = Column(String, index=True)  # Internet 200, 400, 1000, Gig+
    provisioned_download_mbps = Column(Integer)
    provisioned_upload_mbps = Column(Integer)
    monthly_rate = Column(Float)
    contract_status = Column(String)  # active, month_to_month, expired
    tenure_months = Column(Integer)

    # CPE (Customer Premises Equipment)
    modem_mac = Column(String, index=True)
    modem_model = Column(String)
    modem_manufacturer = Column(String)
    docsis_version = Column(String)
    modem_firmware = Column(String)

    # Current performance
    actual_download_mbps = Column(Float)
    actual_upload_mbps = Column(Float)
    connection_drops_24h = Column(Integer)
    last_speed_test = Column(DateTime, nullable=True)
    last_reboot = Column(DateTime, nullable=True)
    uptime_hours = Column(Float)

    # Account status
    account_status = Column(String, index=True)  # active, suspended, closed

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class CustomerSentimentModel(Base):
    """Customer sentiment tracking from multiple sources"""
    __tablename__ = "customer_sentiments"

    __table_args__ = (
        Index('idx_sentiment_account', 'account_id'),
        Index('idx_sentiment_timestamp', 'timestamp'),
        Index('idx_sentiment_source', 'source'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    sentiment_id = Column(String, unique=True, index=True, nullable=False)
    account_id = Column(String, index=True, nullable=False)

    # Source
    source = Column(String, index=True)  # nps_survey, call_center, social_media, app_review, chat
    sentiment_score = Column(Float)  # -1.0 to 1.0
    sentiment_label = Column(String)  # positive, neutral, negative, very_negative
    topics = Column(JSON)  # Array of detected topics
    summary = Column(Text)
    raw_text = Column(Text, nullable=True)

    # NPS specific
    nps_score = Column(Integer, nullable=True)  # 0-10

    # Resolution
    resolution_status = Column(String, nullable=True)  # resolved, unresolved, escalated

    timestamp = Column(DateTime, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TroubleTicketModel(Base):
    """Trouble tickets from auto-detection, customer calls, or proactive monitoring"""
    __tablename__ = "trouble_tickets"

    __table_args__ = (
        Index('idx_ticket_node', 'node_id'),
        Index('idx_ticket_status_priority', 'status', 'priority'),
        Index('idx_ticket_created', 'created_at'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    ticket_id = Column(String, unique=True, index=True, nullable=False)
    account_id = Column(String, index=True, nullable=True)  # Nullable for plant-level tickets
    node_id = Column(String, index=True, nullable=False)

    # Classification
    category = Column(String, index=True)  # service_outage, slow_speed, intermittent, plant_damage, noise_ingress
    priority = Column(String, index=True)  # P1, P2, P3, P4
    status = Column(String, index=True)  # open, assigned, in_progress, resolved, closed

    # Details
    title = Column(String)
    description = Column(Text)

    # Auto-resolution tracking
    auto_resolution_attempted = Column(Boolean, default=False)
    auto_resolution_actions = Column(JSON, nullable=True)  # Actions tried
    auto_resolution_success = Column(Boolean, nullable=True)

    # Dispatch info
    truck_roll_needed = Column(Boolean, default=False)
    tech_skill_level = Column(String, nullable=True)  # L1, L2, L3
    equipment_needed = Column(JSON, nullable=True)
    estimated_resolution_hours = Column(Float, nullable=True)
    assigned_tech = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at = Column(DateTime, nullable=True)
    dispatched_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    # Resolution
    resolution_notes = Column(Text, nullable=True)
    created_by = Column(String)  # auto_detection, customer_call, proactive_monitoring, field_tech
    related_alert_ids = Column(JSON, nullable=True)


# ============================================
# Gating & Maintenance Models
# ============================================

class MaintenanceWindowModel(Base):
    """Maintenance windows with buffer logic"""
    __tablename__ = "maintenance_windows"

    __table_args__ = (
        Index('idx_mw_status', 'status'),
        Index('idx_mw_scheduled', 'scheduled_start', 'scheduled_end'),
        Index('idx_mw_node', 'node_id'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    window_id = Column(String, unique=True, index=True, nullable=False)
    node_id = Column(String, index=True, nullable=True)  # Nullable for area-wide
    headend_id = Column(String, index=True, nullable=True)
    service_area = Column(String, index=True, nullable=True)

    # Classification
    window_type = Column(String, index=True)  # planned_maintenance, emergency, upgrade, plant_construction
    status = Column(String, index=True)  # scheduled, approved, in_progress, completed, cancelled, rescheduled
    priority = Column(String)  # P1, P2, P3, P4

    # Schedule
    scheduled_start = Column(DateTime, nullable=False)
    scheduled_end = Column(DateTime, nullable=False)
    actual_start = Column(DateTime, nullable=True)
    actual_end = Column(DateTime, nullable=True)

    # Buffers
    buffer_before_minutes = Column(Integer, default=30)
    buffer_after_minutes = Column(Integer, default=30)

    # Impact
    affected_homes = Column(Integer, default=0)
    affected_customers = Column(Integer, default=0)
    customer_notification_sent = Column(Boolean, default=False)
    notification_sent_at = Column(DateTime, nullable=True)

    # Details
    reason = Column(String)
    work_description = Column(Text)
    assigned_crew_id = Column(String, nullable=True)
    assigned_crew_name = Column(String, nullable=True)

    # Rescheduling
    reschedule_count = Column(Integer, default=0)
    original_window_id = Column(String, nullable=True)  # Self-FK for rescheduled windows
    rescheduled_reason = Column(String, nullable=True)

    # Approval
    created_by = Column(String)
    approved_by = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class GatingSignalModel(Base):
    """Gating signals for maintenance windows - hard gates vs advisory"""
    __tablename__ = "gating_signals"

    __table_args__ = (
        Index('idx_gate_window', 'maintenance_window_id'),
        Index('idx_gate_status', 'signal_status'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    signal_id = Column(String, unique=True, index=True, nullable=False)
    maintenance_window_id = Column(String, index=True, nullable=False)

    # Signal type
    signal_type = Column(String, index=True)  # weather_check, customer_impact_threshold, concurrent_maintenance_limit, resource_availability, approval_required, peak_hour_block, conflict_check, rollback_readiness
    signal_status = Column(String, index=True)  # pending, passed, failed, overridden, waived
    is_blocking = Column(Boolean, default=True)  # Hard gate vs advisory

    # Evaluation
    evaluated_at = Column(DateTime, nullable=True)
    evaluation_result = Column(JSON, nullable=True)  # Detailed check results
    threshold_value = Column(Float, nullable=True)
    actual_value = Column(Float, nullable=True)

    # Override
    override_by = Column(String, nullable=True)
    override_reason = Column(String, nullable=True)

    description = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ECAFModel(Base):
    """Electronic Change Authorization Form"""
    __tablename__ = "ecafs"

    __table_args__ = (
        Index('idx_ecaf_window', 'maintenance_window_id'),
        Index('idx_ecaf_status', 'status'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    ecaf_id = Column(String, unique=True, index=True, nullable=False)
    maintenance_window_id = Column(String, index=True, nullable=False)

    # Change details
    change_type = Column(String, index=True)  # software_update, hardware_replacement, configuration_change, plant_modification, node_split, cmts_migration
    title = Column(String)
    description = Column(Text)
    risk_level = Column(String, index=True)  # low, medium, high, critical

    # Impact & rollback
    impact_assessment = Column(JSON)  # homes affected, expected downtime, service degradation
    rollback_plan = Column(JSON)  # step-by-step rollback
    rollback_timeout_minutes = Column(Integer)
    pre_change_checks = Column(JSON)  # validation steps
    post_change_checks = Column(JSON)  # verification steps

    # Status & workflow
    status = Column(String, index=True)  # draft, pending_review, approved, rejected, executing, completed, rolled_back, failed
    requested_by = Column(String)
    reviewed_by = Column(String, nullable=True)
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    execution_started_at = Column(DateTime, nullable=True)
    execution_completed_at = Column(DateTime, nullable=True)
    rollback_initiated_at = Column(DateTime, nullable=True)
    rollback_completed_at = Column(DateTime, nullable=True)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class MaintenanceConflictModel(Base):
    """Detected conflicts between maintenance windows"""
    __tablename__ = "maintenance_conflicts"

    __table_args__ = (
        Index('idx_conflict_windows', 'window_a_id', 'window_b_id'),
        Index('idx_conflict_status', 'resolution_status'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    conflict_id = Column(String, unique=True, index=True, nullable=False)
    window_a_id = Column(String, index=True, nullable=False)
    window_b_id = Column(String, index=True, nullable=False)

    # Conflict details
    conflict_type = Column(String, index=True)  # overlapping_time, shared_node, shared_headend, shared_crew, cascading_impact, customer_impact_exceeded
    severity = Column(String, index=True)  # low, medium, high, critical
    description = Column(Text)

    # Resolution
    resolution_status = Column(String, index=True)  # detected, acknowledged, resolved, accepted_risk
    resolved_by = Column(String, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime, nullable=True)


class RollbackEventModel(Base):
    """Rollback events when maintenance or changes fail"""
    __tablename__ = "rollback_events"

    __table_args__ = (
        Index('idx_rollback_ecaf', 'ecaf_id'),
        Index('idx_rollback_window', 'maintenance_window_id'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    rollback_id = Column(String, unique=True, index=True, nullable=False)
    ecaf_id = Column(String, index=True, nullable=False)
    maintenance_window_id = Column(String, index=True, nullable=False)

    # Trigger
    trigger_type = Column(String)  # automatic, manual, timeout
    trigger_reason = Column(Text)

    # Execution
    rollback_steps_executed = Column(JSON)
    rollback_status = Column(String, index=True)  # initiated, in_progress, completed, failed
    initiated_by = Column(String)

    # Timing
    initiated_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Metrics comparison
    pre_rollback_metrics = Column(JSON)
    post_rollback_metrics = Column(JSON)
    success = Column(Boolean, nullable=True)
    notes = Column(Text, nullable=True)


# ============================================
# Dark NOC & AIOps Models
# ============================================

class DarkNOCStateModel(Base):
    """Current state of Dark NOC autonomous operations"""
    __tablename__ = "dark_noc_state"

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    state_id = Column(String, unique=True, index=True, nullable=False)

    # Automation level
    automation_level = Column(String, index=True)  # L0_MANUAL through L5_FULL_AUTONOMY
    current_mode = Column(String)  # dark, supervised, manual

    # Active policies
    active_automation_policies = Column(JSON)  # List of active policy IDs
    human_escalation_threshold = Column(Float, default=0.7)  # Confidence below this escalates

    # 24h metrics
    incidents_auto_resolved_24h = Column(Integer, default=0)
    incidents_escalated_24h = Column(Integer, default=0)
    mean_time_to_detect_seconds = Column(Float, default=0)
    mean_time_to_resolve_seconds = Column(Float, default=0)
    automation_confidence_score = Column(Float, default=80.0)  # 0-100
    last_human_intervention_at = Column(DateTime, nullable=True)
    suppressed_alerts_24h = Column(Integer, default=0)
    correlated_events_24h = Column(Integer, default=0)
    false_positive_rate = Column(Float, default=0)
    operator_override_count_24h = Column(Integer, default=0)

    status = Column(String, default="active")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AutomationPolicyModel(Base):
    """Automation policies for Dark NOC"""
    __tablename__ = "automation_policies"

    __table_args__ = (
        Index('idx_policy_type', 'policy_type'),
        Index('idx_policy_enabled', 'enabled'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    policy_id = Column(String, unique=True, index=True, nullable=False)
    policy_name = Column(String, nullable=False)
    policy_type = Column(String, index=True)  # auto_remediation, auto_escalation, auto_suppression, auto_correlation, predictive_action

    # Trigger and actions
    trigger_conditions = Column(JSON)  # What activates this policy
    actions = Column(JSON)  # What happens when triggered

    # Safety
    risk_level = Column(String)  # low, medium, high
    requires_approval = Column(Boolean, default=False)
    max_autonomous_executions_per_hour = Column(Integer, default=10)
    cooldown_minutes = Column(Integer, default=5)

    # State
    enabled = Column(Boolean, default=True)
    success_rate_threshold = Column(Float, default=0.7)  # Auto-disable if below

    # Stats
    total_executions = Column(Integer, default=0)
    successful_executions = Column(Integer, default=0)
    last_execution_at = Column(DateTime, nullable=True)

    # Ownership
    created_by = Column(String)
    approved_by = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class EventCorrelationModel(Base):
    """Correlated alert clusters with root cause identification"""
    __tablename__ = "event_correlations"

    __table_args__ = (
        Index('idx_correlation_type', 'correlation_type'),
        Index('idx_correlation_created', 'created_at'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    correlation_id = Column(String, unique=True, index=True, nullable=False)

    correlation_type = Column(String, index=True)  # temporal, spatial, causal, topological
    source_alert_ids = Column(JSON)  # All alert IDs in this cluster
    root_cause_alert_id = Column(String, nullable=True)  # Identified root cause
    correlated_alert_count = Column(Integer, default=0)
    suppressed_alert_count = Column(Integer, default=0)
    correlation_confidence = Column(Float)  # 0-1.0

    # Pattern
    correlation_pattern = Column(JSON)  # The detected pattern
    affected_nodes = Column(JSON)
    affected_customers_total = Column(Integer, default=0)

    # Validation
    auto_generated = Column(Boolean, default=True)
    validated_by_operator = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PredictiveModelResultModel(Base):
    """Results from predictive models"""
    __tablename__ = "predictive_model_results"

    __table_args__ = (
        Index('idx_prediction_type', 'model_type'),
        Index('idx_prediction_entity', 'target_entity_type', 'target_entity_id'),
        Index('idx_prediction_time', 'predicted_at'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    prediction_id = Column(String, unique=True, index=True, nullable=False)

    # Model info
    model_type = Column(String, index=True)  # failure_prediction, capacity_forecast, churn_prediction, degradation_forecast, maintenance_need, weather_impact, sentiment_trend
    target_entity_type = Column(String, index=True)  # node, cmts, amplifier, headend, customer, service_area
    target_entity_id = Column(String, index=True)

    # Prediction
    prediction_horizon_hours = Column(Integer)
    predicted_event = Column(String)
    probability = Column(Float)  # 0-1.0
    confidence_interval_low = Column(Float)
    confidence_interval_high = Column(Float)
    contributing_factors = Column(JSON)  # Feature importance

    # Recommended action
    recommended_preemptive_action = Column(Text, nullable=True)
    action_taken = Column(Boolean, default=False)
    action_result = Column(String, nullable=True)

    # Timing
    predicted_at = Column(DateTime, nullable=False)
    prediction_window_start = Column(DateTime)
    prediction_window_end = Column(DateTime)

    # Retrospective accuracy
    actual_outcome = Column(JSON, nullable=True)  # Filled when ground truth available
    accuracy_score = Column(Float, nullable=True)
    model_version = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ImpactModelResultModel(Base):
    """Cascading impact analysis results"""
    __tablename__ = "impact_model_results"

    __table_args__ = (
        Index('idx_impact_scenario', 'scenario_type'),
        Index('idx_impact_computed', 'computed_at'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    impact_id = Column(String, unique=True, index=True, nullable=False)

    # Scenario
    scenario_type = Column(String, index=True)  # node_failure, cmts_failure, headend_outage, plant_damage, maintenance_window, capacity_overload, weather_event
    trigger_entity_id = Column(String, index=True)
    trigger_description = Column(Text)

    # Cascading impacts
    cascading_impacts = Column(JSON)  # Ordered list of downstream effects with timing
    affected_nodes = Column(JSON)
    affected_customers_total = Column(Integer, default=0)
    affected_homes_total = Column(Integer, default=0)

    # Financial
    estimated_revenue_impact = Column(Float, default=0)
    estimated_duration_hours = Column(Float)
    service_degradation_percent = Column(Float)
    customer_experience_score_impact = Column(Float)
    churn_risk_increase_percent = Column(Float)
    sla_breach_probability = Column(Float)

    # Mitigations
    recommended_mitigations = Column(JSON)
    model_confidence = Column(Float)

    computed_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class NOCRunbookModel(Base):
    """Automated runbooks for NOC operations"""
    __tablename__ = "noc_runbooks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    runbook_id = Column(String, unique=True, index=True, nullable=False)
    runbook_name = Column(String, nullable=False)

    # Trigger
    trigger_pattern = Column(JSON)  # Alert patterns that activate this runbook
    category = Column(String, index=True)  # node_ops, cmts_ops, plant_ops, customer_ops, capacity_ops, maintenance_ops

    # Steps
    steps = Column(JSON)  # Ordered automation steps
    escalation_criteria = Column(JSON)  # When to hand off to human
    required_automation_level = Column(String)  # L1-L5

    # Stats
    average_execution_seconds = Column(Float)
    success_rate = Column(Float, default=1.0)
    total_executions = Column(Integer, default=0)
    last_execution_at = Column(DateTime, nullable=True)

    # State
    enabled = Column(Boolean, default=True)
    version = Column(Integer, default=1)
    created_by = Column(String)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class OperatorDecisionLogModel(Base):
    """Audit trail of operator decisions vs AI recommendations"""
    __tablename__ = "operator_decision_log"

    __table_args__ = (
        Index('idx_operator_decision_type', 'decision_type'),
        Index('idx_operator_decision_created', 'created_at'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    decision_id = Column(String, unique=True, index=True, nullable=False)

    operator_id = Column(String)
    operator_name = Column(String)
    decision_type = Column(String, index=True)  # override, escalation, approval, rejection, manual_action

    # Context
    related_alert_id = Column(String, nullable=True)
    related_action_id = Column(String, nullable=True)
    related_ecaf_id = Column(String, nullable=True)

    # Decision details
    ai_recommendation = Column(Text)
    operator_decision = Column(Text)
    reason = Column(Text)

    # Outcome tracking
    outcome = Column(Text, nullable=True)
    outcome_matches_ai = Column(Boolean, nullable=True)  # Did AI's recommendation match what worked?
    feedback_score = Column(Float, nullable=True)  # -1 to 1

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================
# KPI Metrics (transformed for cable network)
# ============================================

class KPIMetricsModel(Base):
    """Real-time KPI metrics for cable fiber nodes"""
    __tablename__ = "kpi_metrics"

    __table_args__ = (
        Index('idx_kpi_node_timestamp', 'node_id', 'timestamp'),
        Index('idx_kpi_timestamp_desc', 'timestamp'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    metric_id = Column(String, unique=True, index=True, nullable=False)
    node_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)

    # RF Signal Levels (DOCSIS)
    ds_power_level_dbmv = Column(Float)  # Downstream power level
    us_power_level_dbmv = Column(Float)  # Upstream power level
    ds_snr_db = Column(Float)  # Downstream SNR
    us_snr_db = Column(Float)  # Upstream SNR
    ds_mer_db = Column(Float)  # Downstream MER (Modulation Error Ratio)
    us_mer_db = Column(Float)  # Upstream MER

    # Forward Error Correction
    fec_corrected_codewords = Column(Integer)
    fec_uncorrected_codewords = Column(Integer)

    # DOCSIS timeouts
    t3_timeouts = Column(Integer)
    t4_timeouts = Column(Integer)

    # Throughput
    downstream_throughput_mbps = Column(Float)
    upstream_throughput_mbps = Column(Float)

    # Network performance
    latency_ms = Column(Float)
    packet_loss_percent = Column(Float)
    jitter_ms = Column(Float)

    # Channel utilization
    ds_channel_utilization_percent = Column(Float)
    us_channel_utilization_percent = Column(Float)
    ofdm_utilization_percent = Column(Float)

    # Modem counts
    active_modems = Column(Integer)
    registered_modems = Column(Integer)
    offline_modems = Column(Integer)
    modems_with_flaps = Column(Integer)

    # Equipment health
    node_temperature = Column(Float)
    node_cpu_utilization = Column(Float)
    node_memory_utilization = Column(Float)
    power_supply_voltage = Column(Float)

    # Weather data
    weather_conditions = Column(String, nullable=True)
    weather_impact = Column(Float, nullable=True)
    temperature_outdoor = Column(Float, nullable=True)
    precipitation_mm = Column(Float, nullable=True)
    wind_speed_kmh = Column(Float, nullable=True)


# ============================================
# Aggregated KPI Tables for Tiered Retention
# ============================================

class KPIMetrics1MinModel(Base):
    """1-minute aggregated KPIs - retained for 6 hours"""
    __tablename__ = "kpi_metrics_1min"

    __table_args__ = (
        Index('idx_kpi_1min_node_timestamp', 'node_id', 'timestamp'),
        Index('idx_kpi_1min_timestamp', 'timestamp'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    node_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)
    sample_count = Column(Integer)
    # Averaged RF metrics
    ds_snr_db = Column(Float)
    us_snr_db = Column(Float)
    ds_power_level_dbmv = Column(Float)
    us_power_level_dbmv = Column(Float)
    latency_ms = Column(Float)
    packet_loss_percent = Column(Float)
    downstream_throughput_mbps = Column(Float)
    upstream_throughput_mbps = Column(Float)
    active_modems = Column(Float)
    node_cpu_utilization = Column(Float)
    node_memory_utilization = Column(Float)
    node_temperature = Column(Float)
    # Min/Max for anomaly detection
    latency_max = Column(Float)
    cpu_max = Column(Float)
    temperature_max = Column(Float)


class KPIMetrics5MinModel(Base):
    """5-minute aggregated KPIs - retained for 24 hours"""
    __tablename__ = "kpi_metrics_5min"

    __table_args__ = (
        Index('idx_kpi_5min_node_timestamp', 'node_id', 'timestamp'),
        Index('idx_kpi_5min_timestamp', 'timestamp'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    node_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)
    sample_count = Column(Integer)
    ds_snr_db = Column(Float)
    us_snr_db = Column(Float)
    ds_power_level_dbmv = Column(Float)
    us_power_level_dbmv = Column(Float)
    latency_ms = Column(Float)
    packet_loss_percent = Column(Float)
    downstream_throughput_mbps = Column(Float)
    upstream_throughput_mbps = Column(Float)
    active_modems = Column(Float)
    node_cpu_utilization = Column(Float)
    node_memory_utilization = Column(Float)
    node_temperature = Column(Float)
    latency_max = Column(Float)
    cpu_max = Column(Float)
    temperature_max = Column(Float)


class KPIMetricsHourlyModel(Base):
    """Hourly aggregated KPIs - retained for 7 days"""
    __tablename__ = "kpi_metrics_hourly"

    __table_args__ = (
        Index('idx_kpi_hourly_node_timestamp', 'node_id', 'timestamp'),
        Index('idx_kpi_hourly_timestamp', 'timestamp'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    node_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)
    sample_count = Column(Integer)
    ds_snr_db = Column(Float)
    us_snr_db = Column(Float)
    ds_power_level_dbmv = Column(Float)
    us_power_level_dbmv = Column(Float)
    latency_ms = Column(Float)
    packet_loss_percent = Column(Float)
    downstream_throughput_mbps = Column(Float)
    upstream_throughput_mbps = Column(Float)
    active_modems = Column(Float)
    node_cpu_utilization = Column(Float)
    node_memory_utilization = Column(Float)
    node_temperature = Column(Float)
    latency_max = Column(Float)
    cpu_max = Column(Float)
    temperature_max = Column(Float)


class KPIMetricsDailyModel(Base):
    """Daily aggregated KPIs - retained for 30 days"""
    __tablename__ = "kpi_metrics_daily"

    __table_args__ = (
        Index('idx_kpi_daily_node_timestamp', 'node_id', 'timestamp'),
        Index('idx_kpi_daily_timestamp', 'timestamp'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    node_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)
    sample_count = Column(Integer)
    ds_snr_db = Column(Float)
    us_snr_db = Column(Float)
    ds_power_level_dbmv = Column(Float)
    us_power_level_dbmv = Column(Float)
    latency_ms = Column(Float)
    packet_loss_percent = Column(Float)
    downstream_throughput_mbps = Column(Float)
    upstream_throughput_mbps = Column(Float)
    active_modems = Column(Float)
    node_cpu_utilization = Column(Float)
    node_memory_utilization = Column(Float)
    node_temperature = Column(Float)
    latency_max = Column(Float)
    cpu_max = Column(Float)
    temperature_max = Column(Float)


# ============================================
# Alerts & Self-Healing (transformed)
# ============================================

class AlertModel(Base):
    """Network alerts - cable network specific"""
    __tablename__ = "alerts"

    __table_args__ = (
        Index('idx_alert_node_timestamp', 'node_id', 'timestamp'),
        Index('idx_alert_status_severity', 'status', 'severity'),
        Index('idx_alert_timestamp_status', 'timestamp', 'status'),
        Index('idx_alert_type_timestamp', 'type', 'timestamp'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    alert_id = Column(String, unique=True, index=True, nullable=False)
    node_id = Column(String, index=True, nullable=False)
    type = Column(String, index=True)
    severity = Column(String, index=True)
    status = Column(String, index=True)
    title = Column(String)
    description = Column(Text)
    timestamp = Column(DateTime, index=True, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    impacted_users = Column(Integer)
    root_cause = Column(Text, nullable=True)
    affected_customers = Column(Integer, default=0)
    affected_modems = Column(Integer, default=0)


class SelfHealingActionModel(Base):
    """Auto-resolution actions for cable network"""
    __tablename__ = "self_healing_actions"

    __table_args__ = (
        Index('idx_action_node_status', 'node_id', 'status'),
        Index('idx_action_status_time', 'status', 'start_time'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    action_id = Column(String, unique=True, index=True, nullable=False)
    alert_id = Column(String, index=True, nullable=True)
    node_id = Column(String, index=True, nullable=False)
    action_type = Column(String, index=True)
    status = Column(String, index=True)
    description = Column(Text)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    effectiveness_score = Column(Float, nullable=True)
    automated = Column(Boolean)
    executed_by = Column(String)
    ticket_id = Column(String, nullable=True)  # FK to trouble ticket if escalated
    escalation_reason = Column(String, nullable=True)


# ============================================
# Kept Models (with minor renames where needed)
# ============================================

class LLMConfigModel(Base):
    __tablename__ = "llm_config"

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    config_key = Column(String, unique=True, index=True, nullable=False, default="default")
    provider = Column(String)
    endpoint_url = Column(String, nullable=True)
    api_key = Column(String, nullable=True)
    jwt_token = Column(Text, nullable=True)
    jwt_token_expires = Column(DateTime, nullable=True)
    model_name = Column(String, nullable=True)
    # Optional second model for natural-language output (per-agent analysis prose,
    # reports, chat). Blank => single-model mode. Pairs a security analyst model
    # (e.g. Cisco Foundation-Sec-8B) with a generalist writer (e.g. Qwen).
    writer_model_name = Column(String, nullable=True)
    # The writer may live on a DIFFERENT endpoint/provider than the analyst.
    # Each blank field falls back to the analyst's value (same endpoint).
    writer_provider = Column(String, nullable=True)
    writer_endpoint_url = Column(String, nullable=True)
    writer_api_key = Column(String, nullable=True)
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2000)
    enabled = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SystemSettingsModel(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    setting_key = Column(String, unique=True, index=True, nullable=False, default="default")
    backend_api_url = Column(String, nullable=True)

    # Slack Integration Settings
    slack_enabled = Column(Boolean, default=False)
    slack_webhook_url = Column(String, nullable=True)
    slack_channel = Column(String, default="#network-alerts")
    slack_notify_alerts = Column(Boolean, default=True)
    slack_notify_actions = Column(Boolean, default=True)
    slack_notify_critical_only = Column(Boolean, default=False)

    # Serper API Settings
    serper_api_key = Column(String, nullable=True)

    # CARTO basemap (map tiles) - key is sent to the browser so Leaflet can fetch tiles
    carto_api_key = Column(String, nullable=True)
    carto_basemap = Column(String, nullable=True)  # light_all, dark_all, voyager, ...

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ClouderaServicesModel(Base):
    """Configuration for all Cloudera Data Platform services"""
    __tablename__ = "cloudera_services"

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    config_key = Column(String, unique=True, index=True, nullable=False, default="default")

    # Apache NiFi - Data ingestion
    nifi_enabled = Column(Boolean, default=False)
    nifi_url = Column(String, nullable=True)
    nifi_username = Column(String, nullable=True)
    nifi_password = Column(String, nullable=True)
    nifi_status = Column(String, default="disconnected")

    # Apache Kafka - Message streaming
    kafka_enabled = Column(Boolean, default=False)
    kafka_bootstrap_servers = Column(String, nullable=True)
    kafka_topics = Column(JSON, nullable=True)
    kafka_security_protocol = Column(String, default="PLAINTEXT")
    kafka_sasl_mechanism = Column(String, nullable=True)
    kafka_username = Column(String, nullable=True)
    kafka_password = Column(String, nullable=True)
    kafka_status = Column(String, default="disconnected")

    # Apache Spark - Stream processing
    spark_enabled = Column(Boolean, default=False)
    spark_master_url = Column(String, nullable=True)
    spark_app_name = Column(String, default="CableNetworkOps")
    spark_executor_memory = Column(String, default="2g")
    spark_executor_cores = Column(Integer, default=2)
    spark_status = Column(String, default="disconnected")

    # Apache Kudu - Real-time storage
    kudu_enabled = Column(Boolean, default=False)
    kudu_master_addresses = Column(String, nullable=True)
    kudu_table_prefix = Column(String, default="cable_")
    kudu_status = Column(String, default="disconnected")

    # Apache Iceberg - Data lakehouse
    iceberg_enabled = Column(Boolean, default=False)
    iceberg_catalog_url = Column(String, nullable=True)
    iceberg_catalog_type = Column(String, default="hive")
    iceberg_warehouse = Column(String, nullable=True)
    iceberg_namespace = Column(String, default="cable_data")
    iceberg_status = Column(String, default="disconnected")

    # Apache Atlas - Data governance
    atlas_enabled = Column(Boolean, default=False)
    atlas_url = Column(String, nullable=True)
    atlas_username = Column(String, nullable=True)
    atlas_password = Column(String, nullable=True)
    atlas_status = Column(String, default="disconnected")

    # Apache Airflow - Workflow orchestration
    airflow_enabled = Column(Boolean, default=False)
    airflow_url = Column(String, nullable=True)
    airflow_username = Column(String, nullable=True)
    airflow_password = Column(String, nullable=True)
    airflow_status = Column(String, default="disconnected")

    # Cloudera ML
    cml_enabled = Column(Boolean, default=False)
    cml_workspace_url = Column(String, nullable=True)
    cml_api_key = Column(String, nullable=True)
    cml_project_name = Column(String, nullable=True)
    cml_status = Column(String, default="disconnected")

    # Cloudera Data Warehouse
    cdw_enabled = Column(Boolean, default=False)
    cdw_jdbc_url = Column(String, nullable=True)
    cdw_username = Column(String, nullable=True)
    cdw_password = Column(String, nullable=True)
    cdw_status = Column(String, default="disconnected")

    # S3 / object storage — edge pcap staging (AWS S3 / Ozone / MinIO).
    # Blank bucket => local-disk staging fallback so the edge demo always runs.
    s3_staging_enabled = Column(Boolean, default=False)
    s3_staging_endpoint_url = Column(String, nullable=True)  # blank = AWS
    s3_staging_access_key = Column(String, nullable=True)
    s3_staging_secret_key = Column(String, nullable=True)
    s3_staging_bucket = Column(String, nullable=True)
    s3_staging_region = Column(String, nullable=True)
    s3_staging_prefix = Column(String, default="edge-captures")
    s3_staging_status = Column(String, default="disconnected")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class HVACUnitModel(Base):
    """HVAC Unit for headend/hub climate control"""
    __tablename__ = "hvac_units"

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    hvac_id = Column(String, unique=True, index=True, nullable=False)
    facility_id = Column(String, index=True, nullable=False)  # headend_id or hub_id
    manufacturer = Column(String, index=True)
    model = Column(String)
    serial_number = Column(String)
    status = Column(String, index=True)

    # Operational parameters
    cooling_capacity_kw = Column(Float)
    heating_capacity_kw = Column(Float)
    current_mode = Column(String)
    setpoint_celsius = Column(Float)
    current_temp_celsius = Column(Float)
    humidity_percent = Column(Float)

    # Performance
    power_consumption_watts = Column(Float)
    compressor_status = Column(String)
    filter_condition = Column(String)
    refrigerant_level_percent = Column(Float)

    # Alarms
    high_temp_alarm = Column(Boolean)
    low_temp_alarm = Column(Boolean)
    compressor_fault = Column(Boolean)

    installed_date = Column(DateTime)
    last_maintenance = Column(DateTime)
    last_filter_change = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ComponentMetricsHistoryModel(Base):
    """Historical metrics for infrastructure components (CMTS, Headend, Hub, Node)"""
    __tablename__ = "component_metrics_history"

    __table_args__ = (
        Index('idx_component_metrics_type_id', 'component_type', 'component_id'),
        Index('idx_component_metrics_timestamp', 'recorded_at'),
    )

    id = Column(Integer, primary_key=True, index=True)
    component_type = Column(String, index=True, nullable=False)  # CMTS, Headend, Hub, Node
    component_id = Column(String, index=True, nullable=False)
    facility_id = Column(String, index=True, nullable=True)  # headend_id

    # Utilization metrics
    utilization_percent = Column(Float)
    cpu_utilization = Column(Float)
    memory_utilization = Column(Float)

    # Capacity metrics
    capacity_current = Column(Float)
    capacity_max = Column(Float)

    # Performance metrics
    performance_score = Column(Float)
    latency_ms = Column(Float)
    error_count = Column(Integer)

    status = Column(String)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class CapacityPlanningExecutionModel(Base):
    """Store capacity planning execution state"""
    __tablename__ = "capacity_planning_executions"

    __table_args__ = (
        Index('idx_capacity_exec_status', 'status'),
        Index('idx_capacity_exec_created', 'created_at'),
    )

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, index=True, nullable=False)

    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    current_agent = Column(String)
    current_agent_name = Column(String)
    progress_percent = Column(Float, default=0.0)

    # Request parameters
    analysis_mode = Column(String, default="current_state")
    target_upgrade_type = Column(String)  # docsis_upgrade, node_split, cmts_expansion
    current_node_type_filter = Column(JSON)
    region = Column(String)
    city = Column(String)
    headend_ids = Column(JSON)
    node_ids = Column(JSON)
    include_nodes = Column(Boolean, default=True)
    include_headends = Column(Boolean, default=True)
    include_cost_estimate = Column(Boolean, default=True)

    # Agent outputs
    thoughts = Column(JSON)
    data_collector_output = Column(JSON)
    upgrade_analysis = Column(JSON)
    hardware_compatibility = Column(JSON)
    headend_analysis = Column(JSON)

    result = Column(JSON)
    error = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ============================================
# AI Analysis Models
# ============================================

class AIInsightModel(Base):
    """AI-generated insights for cable network analysis"""
    __tablename__ = "ai_insights"

    __table_args__ = (
        Index('idx_insight_type_severity', 'insight_type', 'severity'),
        Index('idx_insight_timestamp', 'created_at'),
        Index('idx_insight_expires', 'expires_at'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    insight_id = Column(String, unique=True, index=True, nullable=False)
    insight_type = Column(String, index=True, nullable=False)
    severity = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    affected_node_ids = Column(JSON)
    related_alert_ids = Column(JSON)
    insight_metadata = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime, nullable=True)


class AIAlertAnalysisModel(Base):
    """LLM-powered analysis of individual alerts"""
    __tablename__ = "ai_alert_analyses"

    __table_args__ = (
        Index('idx_analysis_alert', 'alert_id'),
        Index('idx_analysis_node', 'node_id'),
        Index('idx_analysis_timestamp', 'created_at'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    analysis_id = Column(String, unique=True, index=True, nullable=False)
    alert_id = Column(String, index=True, nullable=False)
    node_id = Column(String, index=True, nullable=False)

    summary = Column(Text, nullable=False)
    root_cause = Column(Text, nullable=False)
    recommendations = Column(JSON, nullable=False)
    confidence = Column(Float, nullable=False)
    reasoning = Column(Text)

    should_execute_autonomously = Column(Boolean, default=False)
    urgency_score = Column(Integer, default=5)

    sensor_data_used = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AIActionPlanModel(Base):
    """Autonomous action plans generated by AI"""
    __tablename__ = "ai_action_plans"

    __table_args__ = (
        Index('idx_plan_alert', 'alert_id'),
        Index('idx_plan_node', 'node_id'),
        Index('idx_plan_status', 'status'),
        Index('idx_plan_timestamp', 'created_at'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    plan_id = Column(String, unique=True, index=True, nullable=False)
    alert_id = Column(String, index=True, nullable=False)
    node_id = Column(String, index=True, nullable=False)
    analysis_id = Column(String, index=True, nullable=True)

    root_cause = Column(Text, nullable=False)
    priority = Column(String, index=True, nullable=False)
    status = Column(String, index=True, nullable=False)
    steps = Column(JSON, nullable=False)

    current_step_index = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    execution_log = Column(JSON)
    failure_reason = Column(Text, nullable=True)

    success = Column(Boolean, nullable=True)
    created_actions = Column(JSON)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ============================================
# SLA Configuration & Monitoring
# ============================================

class SLAConfigModel(Base):
    """SLA targets for cable network performance"""
    __tablename__ = "sla_config"

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    config_key = Column(String, unique=True, index=True, nullable=False, default="default")

    # Availability SLAs
    uptime_target_percent = Column(Float, default=99.9)
    max_outage_duration_minutes = Column(Integer, default=30)
    max_monthly_downtime_minutes = Column(Integer, default=43)

    # Latency SLAs
    max_latency_ms = Column(Float, default=30.0)
    latency_p95_target_ms = Column(Float, default=20.0)
    latency_p99_target_ms = Column(Float, default=50.0)

    # Quality SLAs (cable-specific)
    min_ds_snr_db = Column(Float, default=33.0)
    min_us_snr_db = Column(Float, default=25.0)
    max_packet_loss_percent = Column(Float, default=0.5)
    min_throughput_mbps = Column(Float, default=100.0)
    max_fec_uncorrected_rate = Column(Float, default=0.01)

    # Response SLAs
    critical_response_minutes = Column(Integer, default=15)
    warning_response_minutes = Column(Integer, default=60)
    resolution_target_hours = Column(Integer, default=4)

    # Financial Parameters
    revenue_per_subscriber_per_hour = Column(Float, default=0.15)
    cost_per_outage_minute = Column(Float, default=500.0)
    sla_breach_penalty_percent = Column(Float, default=10.0)

    # Alerting Thresholds
    warning_threshold_percent = Column(Float, default=90.0)
    critical_threshold_percent = Column(Float, default=95.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SLABreachModel(Base):
    """Track SLA breaches"""
    __tablename__ = "sla_breaches"

    __table_args__ = (
        Index('idx_breach_node', 'node_id'),
        Index('idx_breach_type', 'breach_type'),
        Index('idx_breach_timestamp', 'breach_start'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    breach_id = Column(String, unique=True, index=True, nullable=False)
    node_id = Column(String, index=True, nullable=True)
    region = Column(String, index=True, nullable=True)

    breach_type = Column(String, index=True, nullable=False)
    metric_name = Column(String, nullable=False)
    sla_target = Column(Float, nullable=False)
    actual_value = Column(Float, nullable=False)
    severity = Column(String, index=True, nullable=False)

    breach_start = Column(DateTime, nullable=False)
    breach_end = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)

    affected_users = Column(Integer, default=0)
    affected_nodes = Column(Integer, default=1)
    financial_impact = Column(Float, default=0.0)

    resolved = Column(Boolean, default=False)
    resolution_notes = Column(Text, nullable=True)
    related_alert_ids = Column(JSON, nullable=True)
    related_action_ids = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ============================================
# Financial Impact Tracking
# ============================================

class FinancialImpactModel(Base):
    """Track financial impact of network events"""
    __tablename__ = "financial_impacts"

    __table_args__ = (
        Index('idx_fin_node', 'node_id'),
        Index('idx_fin_type', 'impact_type'),
        Index('idx_fin_timestamp', 'event_timestamp'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    impact_id = Column(String, unique=True, index=True, nullable=False)

    event_type = Column(String, nullable=False)
    event_id = Column(String, index=True, nullable=True)
    node_id = Column(String, index=True, nullable=True)
    region = Column(String, index=True, nullable=True)

    impact_type = Column(String, index=True, nullable=False)
    category = Column(String, nullable=False)

    gross_impact = Column(Float, nullable=False)
    mitigated_amount = Column(Float, default=0.0)
    net_impact = Column(Float, nullable=False)

    affected_users = Column(Integer, default=0)
    duration_minutes = Column(Integer, default=0)
    calculation_method = Column(String, nullable=True)
    calculation_details = Column(JSON, nullable=True)

    event_timestamp = Column(DateTime, nullable=False)
    resolved_timestamp = Column(DateTime, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FinancialSummaryModel(Base):
    """Daily/monthly financial summaries"""
    __tablename__ = "financial_summaries"

    __table_args__ = (
        Index('idx_finsummary_period', 'period_type', 'period_start'),
        Index('idx_finsummary_region', 'region'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    summary_id = Column(String, unique=True, index=True, nullable=False)

    period_type = Column(String, nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    region = Column(String, index=True, nullable=True)

    total_revenue_at_risk = Column(Float, default=0.0)
    actual_revenue_loss = Column(Float, default=0.0)
    revenue_protected = Column(Float, default=0.0)

    operational_costs = Column(Float, default=0.0)
    sla_penalties = Column(Float, default=0.0)
    ai_savings = Column(Float, default=0.0)

    total_incidents = Column(Integer, default=0)
    auto_resolved_incidents = Column(Integer, default=0)
    manual_interventions = Column(Integer, default=0)
    avg_resolution_time_minutes = Column(Float, default=0.0)

    uptime_percent = Column(Float, default=100.0)
    sla_breaches = Column(Integer, default=0)
    near_breaches = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================
# Digital Twin / Simulation
# ============================================

class SimulationScenarioModel(Base):
    """Store simulation scenarios for Digital Twin"""
    __tablename__ = "simulation_scenarios"

    __table_args__ = (
        Index('idx_sim_type', 'scenario_type'),
        Index('idx_sim_created', 'created_at'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    scenario_id = Column(String, unique=True, index=True, nullable=False)

    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    scenario_type = Column(String, index=True, nullable=False)  # node_failure, plant_damage, capacity, maintenance, weather

    target_nodes = Column(JSON, nullable=True)
    target_regions = Column(JSON, nullable=True)
    target_percentage = Column(Float, nullable=True)

    parameters = Column(JSON, nullable=False)
    duration_minutes = Column(Integer, default=60)

    status = Column(String, default="draft")
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SimulationResultModel(Base):
    """Store results from Digital Twin simulations"""
    __tablename__ = "simulation_results"

    __table_args__ = (
        Index('idx_simresult_scenario', 'scenario_id'),
        Index('idx_simresult_timestamp', 'simulation_start'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    result_id = Column(String, unique=True, index=True, nullable=False)
    scenario_id = Column(String, index=True, nullable=False)

    simulation_start = Column(DateTime, nullable=False)
    simulation_end = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    baseline_metrics = Column(JSON, nullable=False)
    simulated_metrics = Column(JSON, nullable=False)

    affected_nodes = Column(JSON, nullable=False)
    affected_node_count = Column(Integer, default=0)
    affected_customers_estimated = Column(Integer, default=0)
    affected_regions = Column(JSON, nullable=True)

    cascading_failures = Column(JSON, nullable=True)
    neighbor_overload = Column(JSON, nullable=True)

    projected_revenue_loss = Column(Float, default=0.0)
    projected_sla_breaches = Column(Integer, default=0)
    projected_penalty_cost = Column(Float, default=0.0)

    estimated_recovery_time_minutes = Column(Integer, nullable=True)
    recommended_actions = Column(JSON, nullable=True)

    risk_score = Column(Integer, default=0)
    executive_summary = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================
# Network Configuration Management
# ============================================

class NetworkDeviceModel(Base):
    """Unified network device table (firewall, switch, router, modem)"""
    __tablename__ = "network_devices"

    __table_args__ = (
        Index('idx_netdev_type', 'device_type'),
        Index('idx_netdev_status', 'status'),
        Index('idx_netdev_headend', 'headend_id'),
        Index('idx_netdev_hub', 'hub_id'),
        Index('idx_netdev_compliance', 'compliance_status'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String, unique=True, index=True, nullable=False)

    # Classification
    device_type = Column(String, index=True, nullable=False)  # firewall, switch, router, modem
    device_role = Column(String, nullable=True)  # core, distribution, access, edge, perimeter
    hostname = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # Hierarchy links
    headend_id = Column(String, index=True, nullable=True)
    hub_id = Column(String, index=True, nullable=True)
    node_id = Column(String, index=True, nullable=True)
    region = Column(String, index=True, nullable=True)

    # Hardware info
    manufacturer = Column(String, nullable=True)  # Cisco, Fortinet, Palo Alto, Arista, Juniper
    hardware_model = Column(String, nullable=True)
    serial_number = Column(String, nullable=True)
    firmware_version = Column(String, nullable=True)
    os_version = Column(String, nullable=True)

    # Network
    management_ip = Column(String, nullable=True)
    interfaces = Column(JSON, nullable=True)  # [{name, ip, status, speed}]
    uplink_speed_gbps = Column(Float, nullable=True)

    # Status
    status = Column(String, index=True, default="operational")  # operational, degraded, offline, maintenance
    last_seen = Column(DateTime, nullable=True)
    uptime_seconds = Column(Integer, nullable=True)

    # Configuration
    running_config = Column(JSON, nullable=True)   # Device-specific config (ACLs, VLANs, routes, etc.)
    startup_config = Column(JSON, nullable=True)    # Last saved config
    config_hash = Column(String, nullable=True)     # Hash of running config for drift detection
    last_config_change = Column(DateTime, nullable=True)
    last_config_backup = Column(DateTime, nullable=True)

    # Compliance
    compliance_status = Column(String, default="compliant")  # compliant, drifted, non_compliant, unknown
    last_compliance_scan = Column(DateTime, nullable=True)

    # Metrics
    cpu_utilization = Column(Float, nullable=True)
    memory_utilization = Column(Float, nullable=True)
    temperature_celsius = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ConfigurationTemplateModel(Base):
    """Reusable configuration templates per device type/role"""
    __tablename__ = "config_templates"

    __table_args__ = (
        Index('idx_tmpl_type', 'device_type'),
        Index('idx_tmpl_role', 'device_role'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    template_id = Column(String, unique=True, index=True, nullable=False)

    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    device_type = Column(String, index=True, nullable=False)  # firewall, switch, router, modem
    device_role = Column(String, nullable=True)  # core, distribution, access, edge

    # Template content
    config_template = Column(JSON, nullable=False)  # Baseline config for this type/role
    version = Column(String, default="1.0")
    is_active = Column(Boolean, default=True)

    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ConfigChangeLogModel(Base):
    """Audit trail for configuration changes with rollback support"""
    __tablename__ = "config_change_log"

    __table_args__ = (
        Index('idx_changelog_device', 'device_id'),
        Index('idx_changelog_timestamp', 'change_timestamp'),
        Index('idx_changelog_request', 'change_request_id'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    change_id = Column(String, unique=True, index=True, nullable=False)

    device_id = Column(String, index=True, nullable=False)
    change_request_id = Column(String, index=True, nullable=True)

    change_type = Column(String, nullable=False)  # manual, automated, rollback, compliance_fix
    change_description = Column(Text, nullable=True)

    config_before = Column(JSON, nullable=True)
    config_after = Column(JSON, nullable=True)
    config_diff = Column(JSON, nullable=True)  # Summary of what changed

    status = Column(String, default="applied")  # applied, rolled_back, failed
    applied_by = Column(String, nullable=True)  # user or agent name

    change_timestamp = Column(DateTime, nullable=False)
    rollback_available = Column(Boolean, default=True)
    rollback_deadline = Column(DateTime, nullable=True)
    rolled_back_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ConfigComplianceModel(Base):
    """Drift detection records (expected vs actual)"""
    __tablename__ = "config_compliance"

    __table_args__ = (
        Index('idx_compliance_device', 'device_id'),
        Index('idx_compliance_status', 'compliance_status'),
        Index('idx_compliance_scan', 'scan_timestamp'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    compliance_id = Column(String, unique=True, index=True, nullable=False)

    device_id = Column(String, index=True, nullable=False)
    template_id = Column(String, index=True, nullable=True)

    compliance_status = Column(String, nullable=False)  # compliant, drifted, non_compliant
    severity = Column(String, default="low")  # low, medium, high, critical
    drift_details = Column(JSON, nullable=True)  # [{field, expected, actual}]
    drift_count = Column(Integer, default=0)

    scan_timestamp = Column(DateTime, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChangeRequestModel(Base):
    """Groups multi-device changes with approval workflow"""
    __tablename__ = "change_requests"

    __table_args__ = (
        Index('idx_cr_status', 'status'),
        Index('idx_cr_created', 'created_at'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id = Column(String, unique=True, index=True, nullable=False)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    change_type = Column(String, nullable=False)  # security, optimization, compliance, maintenance

    # Target devices
    target_devices = Column(JSON, nullable=False)  # [{device_id, changes: {...}}]
    device_count = Column(Integer, default=0)

    # AI assessment
    ai_risk_assessment = Column(Text, nullable=True)
    ai_impact_score = Column(Float, nullable=True)  # 0-10
    ai_recommendation = Column(String, nullable=True)  # approve, review, reject

    # Workflow
    status = Column(String, index=True, default="pending_review")
    # pending_review, approved, rejected, executing, completed, failed, cancelled, rolled_back

    requested_by = Column(String, nullable=True)  # agent or user
    reviewed_by = Column(String, nullable=True)
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)

    execution_started_at = Column(DateTime, nullable=True)
    execution_completed_at = Column(DateTime, nullable=True)
    execution_log = Column(JSON, nullable=True)
    failure_reason = Column(Text, nullable=True)

    # Rollback
    rollback_available = Column(Boolean, default=False)
    rollback_deadline = Column(DateTime, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ===========================================================================
# Packet-capture analysis + edge anomaly flow
# ===========================================================================


class PcapAnalysisModel(Base):
    """A completed packet-capture analysis (manual upload or edge-ingested).

    Stores the parsed metadata and the four agents' results as JSON so the
    chat/report/docx layers can rehydrate a capture without re-parsing.
    """
    __tablename__ = "pcap_analyses"

    __table_args__ = (
        Index("idx_pcap_created", "created_at"),
        Index("idx_pcap_headend", "headend_id"),
    )

    id = Column(String, primary_key=True, index=True)  # uuid4 hex
    source = Column(String, index=True, default="upload")  # upload | edge
    filename = Column(String, default="")
    headend_id = Column(String, index=True, nullable=True)  # edge origin (HeadendModel.headend_id)
    metadata_json = Column(JSON, nullable=False)
    agents_json = Column(JSON, nullable=False)
    edge_execution_id = Column(String, index=True, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EdgeAnomalyExecutionModel(Base):
    """A triggered edge anomaly event: scripted local-model detection thought-
    stream → staged pcap → primary-DC analysis. Modeled on
    CapacityPlanningExecutionModel (DB-backed so any worker serves polls)."""
    __tablename__ = "edge_anomaly_executions"

    __table_args__ = (
        Index("idx_edge_exec_status", "status"),
        Index("idx_edge_exec_created", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String, unique=True, index=True, nullable=False)  # "edge-<hex12>"
    headend_id = Column(String, index=True, nullable=False)
    headend_name = Column(String, nullable=True)
    scenario_id = Column(String, nullable=False)
    # running | edge_complete | staged | analyzing | completed | failed
    status = Column(String, index=True, nullable=False, default="running")
    progress_percent = Column(Float, default=0.0)

    pcap_source = Column(String, default="bundled")  # bundled | synthesized
    staging_backend = Column(String, default="local")  # s3 | local
    staged_uri = Column(String, nullable=True)
    staged_key = Column(String, nullable=True)

    thoughts = Column(JSON, default=list)       # list[ThoughtMessage]
    edge_actions = Column(JSON, default=list)   # [{action, target, detail, at}]
    analysis_id = Column(String, nullable=True)  # -> PcapAnalysisModel.id
    error = Column(Text, nullable=True)

    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PcapChatMessageModel(Base):
    """Operator chat transcript per capture — feeds the docx report appendix."""
    __tablename__ = "pcap_chat_messages"

    __table_args__ = (Index("idx_pcap_chat_capture", "capture_id"),)

    id = Column(Integer, primary_key=True, index=True)
    capture_id = Column(String, index=True, nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


