"""Pydantic schemas for Cable Network ISP Data Lakehouse API request/response models"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ============================================
# Cable Plant Infrastructure Schemas
# ============================================

class FiberNodeBase(BaseModel):
    node_id: str
    headend_id: Optional[str] = None
    hub_id: Optional[str] = None
    service_area: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    node_type: Optional[str] = None  # N+0, N+1, N+2, N+3
    homes_passed: Optional[int] = None
    homes_active: Optional[int] = None
    docsis_version: Optional[str] = None  # 3.0, 3.1, 4.0
    downstream_channels: Optional[int] = None
    upstream_channels: Optional[int] = None
    ofdm_channels: Optional[int] = None
    ofdma_channels: Optional[int] = None
    manufacturer: Optional[str] = None
    hardware_model: Optional[str] = None
    firmware_version: Optional[str] = None
    power_supply_count: Optional[int] = None
    power_supply_status: Optional[str] = None
    battery_backup_hours: Optional[float] = None
    amplifier_cascade: Optional[int] = None
    coax_plant_miles: Optional[float] = None
    fiber_miles: Optional[float] = None
    tap_count: Optional[int] = None
    status: Optional[str] = None
    upstream_cmts_id: Optional[str] = None
    neighbor_nodes: Optional[List[str]] = None


class FiberNodeCreate(FiberNodeBase):
    pass


class FiberNode(FiberNodeBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class HeadendBase(BaseModel):
    headend_id: str
    name: str
    region: str
    service_area: str
    city: str
    state: str
    latitude: float
    longitude: float
    cmts_count: int
    total_cmts_ports: int
    active_cmts_ports: int
    video_server_count: int
    core_router_count: int
    peering_capacity_gbps: float
    total_rack_units: int
    power_capacity_mw: float
    total_homes_served: int
    total_active_subscribers: int
    status: str


class HeadendCreate(HeadendBase):
    pass


class Headend(HeadendBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CMTSBase(BaseModel):
    cmts_id: str
    headend_id: str
    manufacturer: str
    model: str
    firmware_version: str
    total_ds_ports: int
    total_us_ports: int
    active_modems: int
    registered_modems: int
    offline_modems: int
    max_modems_capacity: int
    avg_ds_utilization: float
    avg_us_utilization: float
    ranging_success_rate: float
    t3_timeouts_24h: int
    t4_timeouts_24h: int
    cpu_utilization: float
    memory_utilization: float
    temperature_celsius: float
    uplink_capacity_gbps: float
    status: str


class CMTSCreate(CMTSBase):
    pass


class CMTS(CMTSBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class HubBase(BaseModel):
    hub_id: str
    headend_id: str
    name: str
    city: str
    state: str
    latitude: float
    longitude: float
    fiber_nodes_served: int
    total_homes_served: int
    fiber_capacity_gbps: float
    current_throughput_gbps: float
    power_status: str
    battery_backup_hours: float
    status: str


class HubCreate(HubBase):
    pass


class Hub(HubBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AmplifierBase(BaseModel):
    amp_id: str
    node_id: str
    manufacturer: str
    model: str
    amp_type: str  # trunk, bridger, line_extender, distribution
    cascade_position: int
    location_type: str  # aerial, pedestal, underground
    ds_input_level: float
    ds_output_level: float
    us_input_level: float
    us_output_level: float
    ds_snr: float
    us_snr: float
    temperature_celsius: float
    power_consumption_watts: float
    power_supply_status: str
    status: str


class AmplifierCreate(AmplifierBase):
    pass


class Amplifier(AmplifierBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================
# Customer / Subscriber Schemas
# ============================================

class CustomerAccountBase(BaseModel):
    account_id: str
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    latitude: float
    longitude: float
    node_id: str
    tap_id: str
    drop_length_ft: float
    drop_quality: str
    service_plan: str
    provisioned_download_mbps: int
    provisioned_upload_mbps: int
    monthly_rate: float
    contract_status: str
    tenure_months: int
    modem_mac: str
    modem_model: str
    modem_manufacturer: str
    docsis_version: str
    modem_firmware: str
    actual_download_mbps: float
    actual_upload_mbps: float
    connection_drops_24h: int
    last_speed_test: Optional[datetime] = None
    last_reboot: Optional[datetime] = None
    uptime_hours: float
    account_status: str


class CustomerAccountCreate(CustomerAccountBase):
    pass


class CustomerAccount(CustomerAccountBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CustomerSentimentBase(BaseModel):
    sentiment_id: str
    account_id: str
    source: str  # nps_survey, call_center, social_media, app_review, chat
    sentiment_score: float  # -1.0 to 1.0
    sentiment_label: str  # positive, neutral, negative, very_negative
    topics: Optional[List[str]] = None
    summary: str
    raw_text: Optional[str] = None
    nps_score: Optional[int] = None
    resolution_status: Optional[str] = None
    timestamp: datetime


class CustomerSentimentCreate(CustomerSentimentBase):
    pass


class CustomerSentiment(CustomerSentimentBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TroubleTicketBase(BaseModel):
    ticket_id: str
    account_id: Optional[str] = None
    node_id: str
    category: str  # service_outage, slow_speed, intermittent, plant_damage, noise_ingress
    priority: str  # P1, P2, P3, P4
    status: str  # open, assigned, in_progress, resolved, closed
    title: str
    description: str
    auto_resolution_attempted: bool = False
    auto_resolution_actions: Optional[List[dict]] = None
    auto_resolution_success: Optional[bool] = None
    truck_roll_needed: bool = False
    tech_skill_level: Optional[str] = None
    equipment_needed: Optional[List[str]] = None
    estimated_resolution_hours: Optional[float] = None
    assigned_tech: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    dispatched_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_by: str
    related_alert_ids: Optional[List[str]] = None


class TroubleTicketCreate(TroubleTicketBase):
    pass


class TroubleTicket(TroubleTicketBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# KPI Metrics Schemas (Cable RF)
# ============================================

class KPIMetricsBase(BaseModel):
    metric_id: str
    node_id: str
    timestamp: datetime
    # RF Signal Levels
    ds_power_level_dbmv: Optional[float] = None
    us_power_level_dbmv: Optional[float] = None
    ds_snr_db: Optional[float] = None
    us_snr_db: Optional[float] = None
    ds_mer_db: Optional[float] = None
    us_mer_db: Optional[float] = None
    # Forward Error Correction
    fec_corrected_codewords: Optional[int] = None
    fec_uncorrected_codewords: Optional[int] = None
    # DOCSIS timeouts
    t3_timeouts: Optional[int] = None
    t4_timeouts: Optional[int] = None
    # Throughput
    downstream_throughput_mbps: Optional[float] = None
    upstream_throughput_mbps: Optional[float] = None
    # Network performance
    latency_ms: Optional[float] = None
    packet_loss_percent: Optional[float] = None
    jitter_ms: Optional[float] = None
    # Channel utilization
    ds_channel_utilization_percent: Optional[float] = None
    us_channel_utilization_percent: Optional[float] = None
    ofdm_utilization_percent: Optional[float] = None
    # Modem counts
    active_modems: Optional[int] = None
    registered_modems: Optional[int] = None
    offline_modems: Optional[int] = None
    modems_with_flaps: Optional[int] = None
    # Equipment health
    node_temperature: Optional[float] = None
    node_cpu_utilization: Optional[float] = None
    node_memory_utilization: Optional[float] = None
    power_supply_voltage: Optional[float] = None
    # Weather data
    weather_conditions: Optional[str] = None
    weather_impact: Optional[float] = None
    temperature_outdoor: Optional[float] = None
    precipitation_mm: Optional[float] = None
    wind_speed_kmh: Optional[float] = None


class KPIMetricsCreate(KPIMetricsBase):
    pass


class KPIMetrics(KPIMetricsBase):
    id: int

    class Config:
        from_attributes = True


# ============================================
# Alert Schemas
# ============================================

class AlertBase(BaseModel):
    alert_id: str
    node_id: str
    type: str
    severity: str
    status: str
    title: Optional[str] = None
    description: Optional[str] = None
    timestamp: datetime
    resolved_at: Optional[datetime] = None
    impacted_users: Optional[int] = None
    root_cause: Optional[str] = None
    affected_customers: int = 0
    affected_modems: int = 0


class AlertCreate(AlertBase):
    pass


class Alert(AlertBase):
    id: int

    class Config:
        from_attributes = True


# ============================================
# Self-Healing Action Schemas
# ============================================

class SelfHealingActionBase(BaseModel):
    action_id: str
    alert_id: Optional[str] = None
    node_id: str
    action_type: str
    status: str
    description: str
    start_time: datetime
    end_time: Optional[datetime] = None
    effectiveness_score: Optional[float] = None
    automated: Optional[bool] = True
    executed_by: Optional[str] = "system"
    ticket_id: Optional[str] = None
    escalation_reason: Optional[str] = None


class SelfHealingActionCreate(SelfHealingActionBase):
    pass


class SelfHealingAction(SelfHealingActionBase):
    id: int

    class Config:
        from_attributes = True


# ============================================
# Gating & Maintenance Schemas
# ============================================

class MaintenanceWindowBase(BaseModel):
    window_id: str
    node_id: Optional[str] = None
    headend_id: Optional[str] = None
    service_area: Optional[str] = None
    window_type: str  # planned_maintenance, emergency, upgrade, plant_construction
    status: str  # scheduled, approved, in_progress, completed, cancelled, rescheduled
    priority: str  # P1, P2, P3, P4
    scheduled_start: datetime
    scheduled_end: datetime
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    buffer_before_minutes: int = 30
    buffer_after_minutes: int = 30
    affected_homes: int = 0
    affected_customers: int = 0
    customer_notification_sent: bool = False
    notification_sent_at: Optional[datetime] = None
    reason: str
    work_description: str
    assigned_crew_id: Optional[str] = None
    assigned_crew_name: Optional[str] = None
    reschedule_count: int = 0
    original_window_id: Optional[str] = None
    rescheduled_reason: Optional[str] = None
    created_by: str
    approved_by: Optional[str] = None


class MaintenanceWindowCreate(MaintenanceWindowBase):
    pass


class MaintenanceWindow(MaintenanceWindowBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GatingSignalBase(BaseModel):
    signal_id: str
    maintenance_window_id: str
    signal_type: str  # weather_check, customer_impact_threshold, concurrent_maintenance_limit, resource_availability, approval_required, peak_hour_block, conflict_check, rollback_readiness
    signal_status: str  # pending, passed, failed, overridden, waived
    is_blocking: bool = True
    evaluated_at: Optional[datetime] = None
    evaluation_result: Optional[dict] = None
    threshold_value: Optional[float] = None
    actual_value: Optional[float] = None
    override_by: Optional[str] = None
    override_reason: Optional[str] = None
    description: str


class GatingSignalCreate(GatingSignalBase):
    pass


class GatingSignal(GatingSignalBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ECAFBase(BaseModel):
    ecaf_id: str
    maintenance_window_id: str
    change_type: str  # software_update, hardware_replacement, configuration_change, plant_modification, node_split, cmts_migration
    title: str
    description: str
    risk_level: str  # low, medium, high, critical
    impact_assessment: Optional[dict] = None
    rollback_plan: Optional[dict] = None
    rollback_timeout_minutes: int = 60
    pre_change_checks: Optional[List[dict]] = None
    post_change_checks: Optional[List[dict]] = None
    status: str  # draft, pending_review, approved, rejected, executing, completed, rolled_back, failed
    requested_by: str
    reviewed_by: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    execution_started_at: Optional[datetime] = None
    execution_completed_at: Optional[datetime] = None
    rollback_initiated_at: Optional[datetime] = None
    rollback_completed_at: Optional[datetime] = None
    notes: Optional[str] = None


class ECAFCreate(ECAFBase):
    pass


class ECAF(ECAFBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MaintenanceConflictBase(BaseModel):
    conflict_id: str
    window_a_id: str
    window_b_id: str
    conflict_type: str  # overlapping_time, shared_node, shared_headend, shared_crew, cascading_impact, customer_impact_exceeded
    severity: str  # low, medium, high, critical
    description: str
    resolution_status: str  # detected, acknowledged, resolved, accepted_risk
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None


class MaintenanceConflictCreate(MaintenanceConflictBase):
    pass


class MaintenanceConflict(MaintenanceConflictBase):
    id: int
    detected_at: datetime

    class Config:
        from_attributes = True


class RollbackEventBase(BaseModel):
    rollback_id: str
    ecaf_id: str
    maintenance_window_id: str
    trigger_type: str  # automatic, manual, timeout
    trigger_reason: str
    rollback_steps_executed: Optional[List[dict]] = None
    rollback_status: str  # initiated, in_progress, completed, failed
    initiated_by: str
    initiated_at: datetime
    completed_at: Optional[datetime] = None
    pre_rollback_metrics: Optional[dict] = None
    post_rollback_metrics: Optional[dict] = None
    success: Optional[bool] = None
    notes: Optional[str] = None


class RollbackEventCreate(RollbackEventBase):
    pass


class RollbackEvent(RollbackEventBase):
    id: int

    class Config:
        from_attributes = True


# ============================================
# Gating Evaluation Request/Response
# ============================================

class GatingEvaluationRequest(BaseModel):
    """Request to evaluate all gates for a maintenance window"""
    maintenance_window_id: str
    force_reevaluate: bool = False


class GatingEvaluationResponse(BaseModel):
    """Response from gate evaluation"""
    maintenance_window_id: str
    overall_status: str  # go, no_go, advisory_warnings
    gates: List[GatingSignal]
    blocking_failures: int
    advisory_warnings: int
    all_passed: bool
    evaluated_at: datetime


class MaintenanceScheduleRequest(BaseModel):
    """Request to schedule a new maintenance window"""
    node_id: Optional[str] = None
    headend_id: Optional[str] = None
    service_area: Optional[str] = None
    window_type: str
    scheduled_start: datetime
    scheduled_end: datetime
    reason: str
    work_description: str
    priority: str = "P3"
    buffer_before_minutes: int = 30
    buffer_after_minutes: int = 30


class ConflictCheckResponse(BaseModel):
    """Response from conflict check"""
    conflicts_found: int
    conflicts: List[MaintenanceConflict]
    can_proceed: bool
    recommendation: str


# ============================================
# Dark NOC & AIOps Schemas
# ============================================

class DarkNOCStateBase(BaseModel):
    state_id: str
    automation_level: str  # L0_MANUAL through L5_FULL_AUTONOMY
    current_mode: str  # dark, supervised, manual
    active_automation_policies: Optional[List[str]] = None
    human_escalation_threshold: float = 0.7
    incidents_auto_resolved_24h: int = 0
    incidents_escalated_24h: int = 0
    mean_time_to_detect_seconds: float = 0
    mean_time_to_resolve_seconds: float = 0
    automation_confidence_score: float = 80.0
    last_human_intervention_at: Optional[datetime] = None
    suppressed_alerts_24h: int = 0
    correlated_events_24h: int = 0
    false_positive_rate: float = 0
    operator_override_count_24h: int = 0
    status: str = "active"


class DarkNOCState(DarkNOCStateBase):
    id: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DarkNOCStateUpdate(BaseModel):
    """Update automation level or mode"""
    automation_level: Optional[str] = None
    current_mode: Optional[str] = None
    human_escalation_threshold: Optional[float] = None


class AutomationPolicyBase(BaseModel):
    policy_id: str
    policy_name: str
    policy_type: str  # auto_remediation, auto_escalation, auto_suppression, auto_correlation, predictive_action
    trigger_conditions: Optional[dict] = None
    actions: Optional[dict] = None
    risk_level: str
    requires_approval: bool = False
    max_autonomous_executions_per_hour: int = 10
    cooldown_minutes: int = 5
    enabled: bool = True
    success_rate_threshold: float = 0.7
    total_executions: int = 0
    successful_executions: int = 0
    last_execution_at: Optional[datetime] = None
    created_by: str
    approved_by: Optional[str] = None


class AutomationPolicyCreate(AutomationPolicyBase):
    pass


class AutomationPolicy(AutomationPolicyBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EventCorrelationBase(BaseModel):
    correlation_id: str
    correlation_type: str  # temporal, spatial, causal, topological
    source_alert_ids: Optional[List[str]] = None
    root_cause_alert_id: Optional[str] = None
    correlated_alert_count: int = 0
    suppressed_alert_count: int = 0
    correlation_confidence: float
    correlation_pattern: Optional[dict] = None
    affected_nodes: Optional[List[str]] = None
    affected_customers_total: int = 0
    auto_generated: bool = True
    validated_by_operator: bool = False


class EventCorrelation(EventCorrelationBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class PredictiveModelResultBase(BaseModel):
    prediction_id: str
    model_type: str  # failure_prediction, capacity_forecast, churn_prediction, degradation_forecast, maintenance_need, weather_impact, sentiment_trend
    target_entity_type: str  # node, cmts, amplifier, headend, customer, service_area
    target_entity_id: str
    prediction_horizon_hours: int
    predicted_event: str
    probability: float  # 0-1.0
    confidence_interval_low: float
    confidence_interval_high: float
    contributing_factors: Optional[dict] = None
    recommended_preemptive_action: Optional[str] = None
    action_taken: bool = False
    action_result: Optional[str] = None
    predicted_at: datetime
    prediction_window_start: Optional[datetime] = None
    prediction_window_end: Optional[datetime] = None
    actual_outcome: Optional[dict] = None
    accuracy_score: Optional[float] = None
    model_version: Optional[str] = None


class PredictiveModelResult(PredictiveModelResultBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ImpactModelResultBase(BaseModel):
    impact_id: str
    scenario_type: str  # node_failure, cmts_failure, headend_outage, plant_damage, maintenance_window, capacity_overload, weather_event
    trigger_entity_id: str
    trigger_description: str
    cascading_impacts: Optional[List[dict]] = None
    affected_nodes: Optional[List[str]] = None
    affected_customers_total: int = 0
    affected_homes_total: int = 0
    estimated_revenue_impact: float = 0
    estimated_duration_hours: float = 0
    service_degradation_percent: float = 0
    customer_experience_score_impact: float = 0
    churn_risk_increase_percent: float = 0
    sla_breach_probability: float = 0
    recommended_mitigations: Optional[List[dict]] = None
    model_confidence: float = 0
    computed_at: datetime


class ImpactModelResult(ImpactModelResultBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ImpactModelRunRequest(BaseModel):
    """Request to run impact model for a scenario"""
    scenario_type: str
    trigger_entity_id: str
    trigger_description: Optional[str] = None


class ImpactModelCompareRequest(BaseModel):
    """Compare multiple impact model scenarios"""
    impact_ids: List[str]


class NOCRunbookBase(BaseModel):
    runbook_id: str
    runbook_name: str
    trigger_pattern: Optional[dict] = None
    category: str  # node_ops, cmts_ops, plant_ops, customer_ops, capacity_ops, maintenance_ops
    steps: Optional[List[dict]] = None
    escalation_criteria: Optional[dict] = None
    required_automation_level: str
    average_execution_seconds: float = 0
    success_rate: float = 1.0
    total_executions: int = 0
    last_execution_at: Optional[datetime] = None
    enabled: bool = True
    version: int = 1
    created_by: str


class NOCRunbookCreate(NOCRunbookBase):
    pass


class NOCRunbook(NOCRunbookBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OperatorDecisionLogBase(BaseModel):
    decision_id: str
    operator_id: str
    operator_name: str
    decision_type: str  # override, escalation, approval, rejection, manual_action
    related_alert_id: Optional[str] = None
    related_action_id: Optional[str] = None
    related_ecaf_id: Optional[str] = None
    ai_recommendation: str
    operator_decision: str
    reason: str
    outcome: Optional[str] = None
    outcome_matches_ai: Optional[bool] = None
    feedback_score: Optional[float] = None


class OperatorDecisionLog(OperatorDecisionLogBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class DarkNOCMetricsResponse(BaseModel):
    """Aggregate Dark NOC performance metrics"""
    mean_time_to_detect_seconds: float
    mean_time_to_resolve_seconds: float
    auto_resolve_rate: float
    false_positive_rate: float
    suppression_rate: float
    automation_confidence: float
    incidents_auto_resolved_24h: int
    incidents_escalated_24h: int
    operator_overrides_24h: int
    correlated_events_24h: int
    active_policies: int
    active_runbooks: int


# ============================================
# Pagination
# ============================================

class PaginationParams(BaseModel):
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(100, ge=1, le=1000, description="Number of records to return")


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List


class FiberNodeListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[FiberNode]


class HeadendListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[Headend]


class CMTSListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[CMTS]


class HubListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[Hub]


class AmplifierListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[Amplifier]


class CustomerAccountListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[CustomerAccount]


class CustomerSentimentListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[CustomerSentiment]


class TroubleTicketListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[TroubleTicket]


class KPIMetricsListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[KPIMetrics]


class AlertListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[Alert]


class ActionListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[SelfHealingAction]


class MaintenanceWindowListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[MaintenanceWindow]


class GatingSignalListResponse(BaseModel):
    total: int
    items: List[GatingSignal]


class ECAFListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[ECAF]


class MaintenanceConflictListResponse(BaseModel):
    total: int
    items: List[MaintenanceConflict]


class RollbackEventListResponse(BaseModel):
    total: int
    items: List[RollbackEvent]


class PredictiveModelResultListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[PredictiveModelResult]


class ImpactModelResultListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[ImpactModelResult]


class EventCorrelationListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[EventCorrelation]


class AutomationPolicyListResponse(BaseModel):
    total: int
    items: List[AutomationPolicy]


class NOCRunbookListResponse(BaseModel):
    total: int
    items: List[NOCRunbook]


class OperatorDecisionLogListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[OperatorDecisionLog]


# ============================================
# Generation Request Schemas
# ============================================

class GenerateNodesRequest(BaseModel):
    count: int = Field(10000, ge=1, le=10000, description="Number of fiber nodes to generate")
    service_area: Optional[str] = Field(None, description="Specific service area to generate nodes for")


class GenerateKPIsRequest(BaseModel):
    node_ids: Optional[List[str]] = Field(None, description="Specific node IDs to generate KPIs for")
    count: int = Field(100, ge=1, le=10000, description="Number of KPI records to generate per node")


class GenerateAlertsRequest(BaseModel):
    node_ids: Optional[List[str]] = Field(None, description="Specific node IDs to generate alerts for")
    count: int = Field(10, ge=1, le=1000, description="Number of alerts to generate")


class GenerateActionsRequest(BaseModel):
    alert_ids: Optional[List[str]] = Field(None, description="Specific alert IDs to generate actions for")
    count: int = Field(10, ge=1, le=1000, description="Number of actions to generate")


class GenerateCustomersRequest(BaseModel):
    node_ids: Optional[List[str]] = Field(None, description="Specific node IDs to generate customers for")
    batch_size: int = Field(5000, ge=1, le=50000, description="Batch size for customer generation")


# ============================================
# LLM Configuration Schemas
# ============================================

class LLMConfigBase(BaseModel):
    provider: str = Field(..., description="LLM provider: openai, anthropic, ollama, cloudera, custom")
    endpoint_url: Optional[str] = Field(None, description="Custom endpoint URL")
    api_key: Optional[str] = Field(None, description="API key for the provider")
    jwt_token: Optional[str] = Field(None, description="JWT token for authentication")
    jwt_token_expires: Optional[datetime] = Field(None, description="JWT token expiration time")
    model_name: Optional[str] = Field(None, description="Model name to use (analyst / detection)")
    writer_model_name: Optional[str] = Field(None, description="Optional generalist model for prose/reports/chat; blank => single-model")
    writer_provider: Optional[str] = Field(None, description="Writer provider; blank => same as analyst")
    writer_endpoint_url: Optional[str] = Field(None, description="Writer endpoint URL; blank => same as analyst")
    writer_api_key: Optional[str] = Field(None, description="Writer API key/token; blank => same as analyst")
    temperature: float = Field(0.7, ge=0, le=2, description="Temperature for generation")
    max_tokens: int = Field(2000, ge=1, le=100000, description="Maximum tokens to generate")
    enabled: bool = Field(False, description="Whether LLM is enabled")


class LLMConfigCreate(LLMConfigBase):
    pass


class LLMConfigUpdate(BaseModel):
    provider: Optional[str] = None
    endpoint_url: Optional[str] = None
    api_key: Optional[str] = None
    jwt_token: Optional[str] = None
    jwt_token_expires: Optional[datetime] = None
    model_name: Optional[str] = None
    writer_model_name: Optional[str] = None
    writer_provider: Optional[str] = None
    writer_endpoint_url: Optional[str] = None
    writer_api_key: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    enabled: Optional[bool] = None


class LLMConfig(LLMConfigBase):
    id: int
    config_key: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================
# System Settings Schemas
# ============================================

class SystemSettingsBase(BaseModel):
    backend_api_url: Optional[str] = None
    slack_enabled: bool = False
    slack_webhook_url: Optional[str] = None
    slack_channel: str = "#network-alerts"
    slack_notify_alerts: bool = True
    slack_notify_actions: bool = True
    slack_notify_critical_only: bool = False
    serper_api_key: Optional[str] = None
    carto_api_key: Optional[str] = None
    carto_basemap: Optional[str] = None


class SystemSettingsCreate(SystemSettingsBase):
    pass


class SystemSettings(SystemSettingsBase):
    id: int
    setting_key: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================
# Cloudera Services Schemas
# ============================================

class ClouderaServicesBase(BaseModel):
    # Apache NiFi - Data ingestion
    nifi_enabled: bool = False
    nifi_url: Optional[str] = None
    nifi_username: Optional[str] = None
    nifi_password: Optional[str] = None

    # Apache Kafka - Message streaming
    kafka_enabled: bool = False
    kafka_bootstrap_servers: Optional[str] = None
    kafka_topics: Optional[List[str]] = None
    kafka_security_protocol: str = "PLAINTEXT"
    kafka_sasl_mechanism: Optional[str] = None
    kafka_username: Optional[str] = None
    kafka_password: Optional[str] = None

    # Apache Spark - Stream processing
    spark_enabled: bool = False
    spark_master_url: Optional[str] = None
    spark_app_name: str = "CableNetworkOps"
    spark_executor_memory: str = "2g"
    spark_executor_cores: int = 2

    # Apache Kudu - Real-time storage
    kudu_enabled: bool = False
    kudu_master_addresses: Optional[str] = None
    kudu_table_prefix: str = "cable_"

    # Apache Iceberg - Data lakehouse
    iceberg_enabled: bool = False
    iceberg_catalog_url: Optional[str] = None
    iceberg_catalog_type: str = "hive"
    iceberg_warehouse: Optional[str] = None
    iceberg_namespace: str = "cable_data"

    # Apache Atlas - Data governance
    atlas_enabled: bool = False
    atlas_url: Optional[str] = None
    atlas_username: Optional[str] = None
    atlas_password: Optional[str] = None

    # Apache Airflow - Workflow orchestration
    airflow_enabled: bool = False
    airflow_url: Optional[str] = None
    airflow_username: Optional[str] = None
    airflow_password: Optional[str] = None

    # Cloudera ML - Machine Learning
    cml_enabled: bool = False
    cml_workspace_url: Optional[str] = None
    cml_api_key: Optional[str] = None
    cml_project_name: Optional[str] = None

    # Cloudera Data Warehouse (CDW) - Analytics
    cdw_enabled: bool = False
    cdw_jdbc_url: Optional[str] = None
    cdw_username: Optional[str] = None
    cdw_password: Optional[str] = None

    # S3 / object storage - edge pcap staging (blank bucket => local fallback)
    s3_staging_enabled: bool = False
    s3_staging_endpoint_url: Optional[str] = None
    s3_staging_access_key: Optional[str] = None
    s3_staging_secret_key: Optional[str] = None
    s3_staging_bucket: Optional[str] = None
    s3_staging_region: Optional[str] = None
    s3_staging_prefix: str = "edge-captures"


class ClouderaServicesCreate(ClouderaServicesBase):
    pass


class ClouderaServicesUpdate(BaseModel):
    nifi_enabled: Optional[bool] = None
    nifi_url: Optional[str] = None
    nifi_username: Optional[str] = None
    nifi_password: Optional[str] = None
    kafka_enabled: Optional[bool] = None
    kafka_bootstrap_servers: Optional[str] = None
    kafka_topics: Optional[List[str]] = None
    kafka_security_protocol: Optional[str] = None
    kafka_sasl_mechanism: Optional[str] = None
    kafka_username: Optional[str] = None
    kafka_password: Optional[str] = None
    spark_enabled: Optional[bool] = None
    spark_master_url: Optional[str] = None
    spark_app_name: Optional[str] = None
    spark_executor_memory: Optional[str] = None
    spark_executor_cores: Optional[int] = None
    kudu_enabled: Optional[bool] = None
    kudu_master_addresses: Optional[str] = None
    kudu_table_prefix: Optional[str] = None
    iceberg_enabled: Optional[bool] = None
    iceberg_catalog_url: Optional[str] = None
    iceberg_catalog_type: Optional[str] = None
    iceberg_warehouse: Optional[str] = None
    iceberg_namespace: Optional[str] = None
    atlas_enabled: Optional[bool] = None
    atlas_url: Optional[str] = None
    atlas_username: Optional[str] = None
    atlas_password: Optional[str] = None
    airflow_enabled: Optional[bool] = None
    airflow_url: Optional[str] = None
    airflow_username: Optional[str] = None
    airflow_password: Optional[str] = None
    cml_enabled: Optional[bool] = None
    cml_workspace_url: Optional[str] = None
    cml_api_key: Optional[str] = None
    cml_project_name: Optional[str] = None
    cdw_enabled: Optional[bool] = None
    cdw_jdbc_url: Optional[str] = None
    cdw_username: Optional[str] = None
    cdw_password: Optional[str] = None
    s3_staging_enabled: Optional[bool] = None
    s3_staging_endpoint_url: Optional[str] = None
    s3_staging_access_key: Optional[str] = None
    s3_staging_secret_key: Optional[str] = None
    s3_staging_bucket: Optional[str] = None
    s3_staging_region: Optional[str] = None
    s3_staging_prefix: Optional[str] = None


class ClouderaServices(ClouderaServicesBase):
    id: int
    config_key: str
    nifi_status: str = "disconnected"
    kafka_status: str = "disconnected"
    spark_status: str = "disconnected"
    kudu_status: str = "disconnected"
    iceberg_status: str = "disconnected"
    atlas_status: str = "disconnected"
    airflow_status: str = "disconnected"
    cml_status: str = "disconnected"
    cdw_status: str = "disconnected"
    s3_staging_status: str = "disconnected"
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ClouderaServiceStatus(BaseModel):
    """Status response for a single Cloudera service"""
    service: str
    enabled: bool
    status: str  # connected, disconnected, error
    message: Optional[str] = None
    last_check: Optional[datetime] = None


# ============================================
# Secure Response Schemas (mask sensitive data)
# ============================================

def mask_secret(value: Optional[str]) -> Optional[str]:
    """Mask a secret value, showing only last 4 chars"""
    if not value:
        return None
    if len(value) <= 4:
        return "****"
    return "*" * (len(value) - 4) + value[-4:]


class LLMConfigResponse(BaseModel):
    """Secure response schema for LLM config - masks sensitive fields"""
    id: int
    config_key: str
    provider: str
    endpoint_url: Optional[str] = None
    api_key_set: bool = False
    jwt_token_set: bool = False
    jwt_token_expires: Optional[datetime] = None
    model_name: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    enabled: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_model(cls, model) -> "LLMConfigResponse":
        return cls(
            id=model.id,
            config_key=model.config_key,
            provider=model.provider,
            endpoint_url=model.endpoint_url,
            api_key_set=bool(model.api_key),
            jwt_token_set=bool(model.jwt_token),
            jwt_token_expires=model.jwt_token_expires,
            model_name=model.model_name,
            temperature=model.temperature,
            max_tokens=model.max_tokens,
            enabled=model.enabled,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SystemSettingsResponse(BaseModel):
    """Secure response schema for system settings - masks sensitive fields"""
    id: int
    setting_key: str
    backend_api_url: Optional[str] = None
    slack_enabled: bool = False
    slack_webhook_configured: bool = False
    slack_channel: str = "#network-alerts"
    slack_notify_alerts: bool = True
    slack_notify_actions: bool = True
    slack_notify_critical_only: bool = False
    serper_api_key_set: bool = False
    carto_api_key_set: bool = False
    carto_basemap: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_model(cls, model) -> "SystemSettingsResponse":
        return cls(
            id=model.id,
            setting_key=model.setting_key,
            backend_api_url=model.backend_api_url,
            slack_enabled=model.slack_enabled,
            slack_webhook_configured=bool(model.slack_webhook_url),
            slack_channel=model.slack_channel,
            slack_notify_alerts=model.slack_notify_alerts,
            slack_notify_actions=model.slack_notify_actions,
            slack_notify_critical_only=model.slack_notify_critical_only,
            serper_api_key_set=bool(model.serper_api_key),
            carto_api_key_set=bool(model.carto_api_key),
            carto_basemap=model.carto_basemap,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class ClouderaServicesResponse(BaseModel):
    """Secure response schema for Cloudera services - masks all passwords/keys"""
    id: int
    config_key: str
    # NiFi
    nifi_enabled: bool = False
    nifi_url: Optional[str] = None
    nifi_username: Optional[str] = None
    nifi_password_set: bool = False
    nifi_status: str = "disconnected"
    # Kafka
    kafka_enabled: bool = False
    kafka_bootstrap_servers: Optional[str] = None
    kafka_topics: Optional[List[str]] = None
    kafka_security_protocol: str = "PLAINTEXT"
    kafka_sasl_mechanism: Optional[str] = None
    kafka_username: Optional[str] = None
    kafka_password_set: bool = False
    kafka_status: str = "disconnected"
    # Spark
    spark_enabled: bool = False
    spark_master_url: Optional[str] = None
    spark_app_name: str = "CableNetworkOps"
    spark_executor_memory: str = "2g"
    spark_executor_cores: int = 2
    spark_status: str = "disconnected"
    # Kudu
    kudu_enabled: bool = False
    kudu_master_addresses: Optional[str] = None
    kudu_table_prefix: str = "cable_"
    kudu_status: str = "disconnected"
    # Iceberg
    iceberg_enabled: bool = False
    iceberg_catalog_url: Optional[str] = None
    iceberg_catalog_type: str = "hive"
    iceberg_warehouse: Optional[str] = None
    iceberg_namespace: str = "cable_data"
    iceberg_status: str = "disconnected"
    # Atlas
    atlas_enabled: bool = False
    atlas_url: Optional[str] = None
    atlas_username: Optional[str] = None
    atlas_password_set: bool = False
    atlas_status: str = "disconnected"
    # Airflow
    airflow_enabled: bool = False
    airflow_url: Optional[str] = None
    airflow_username: Optional[str] = None
    airflow_password_set: bool = False
    airflow_status: str = "disconnected"
    # CML
    cml_enabled: bool = False
    cml_workspace_url: Optional[str] = None
    cml_api_key_set: bool = False
    cml_project_name: Optional[str] = None
    cml_status: str = "disconnected"
    # CDW
    cdw_enabled: bool = False
    cdw_jdbc_url: Optional[str] = None
    cdw_username: Optional[str] = None
    cdw_password_set: bool = False
    cdw_status: str = "disconnected"
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_model(cls, model) -> "ClouderaServicesResponse":
        return cls(
            id=model.id,
            config_key=model.config_key,
            nifi_enabled=model.nifi_enabled,
            nifi_url=model.nifi_url,
            nifi_username=model.nifi_username,
            nifi_password_set=bool(model.nifi_password),
            nifi_status=model.nifi_status,
            kafka_enabled=model.kafka_enabled,
            kafka_bootstrap_servers=model.kafka_bootstrap_servers,
            kafka_topics=model.kafka_topics,
            kafka_security_protocol=model.kafka_security_protocol,
            kafka_sasl_mechanism=model.kafka_sasl_mechanism,
            kafka_username=model.kafka_username,
            kafka_password_set=bool(model.kafka_password),
            kafka_status=model.kafka_status,
            spark_enabled=model.spark_enabled,
            spark_master_url=model.spark_master_url,
            spark_app_name=model.spark_app_name,
            spark_executor_memory=model.spark_executor_memory,
            spark_executor_cores=model.spark_executor_cores,
            spark_status=model.spark_status,
            kudu_enabled=model.kudu_enabled,
            kudu_master_addresses=model.kudu_master_addresses,
            kudu_table_prefix=model.kudu_table_prefix,
            kudu_status=model.kudu_status,
            iceberg_enabled=model.iceberg_enabled,
            iceberg_catalog_url=model.iceberg_catalog_url,
            iceberg_catalog_type=model.iceberg_catalog_type,
            iceberg_warehouse=model.iceberg_warehouse,
            iceberg_namespace=model.iceberg_namespace,
            iceberg_status=model.iceberg_status,
            atlas_enabled=model.atlas_enabled,
            atlas_url=model.atlas_url,
            atlas_username=model.atlas_username,
            atlas_password_set=bool(model.atlas_password),
            atlas_status=model.atlas_status,
            airflow_enabled=model.airflow_enabled,
            airflow_url=model.airflow_url,
            airflow_username=model.airflow_username,
            airflow_password_set=bool(model.airflow_password),
            airflow_status=model.airflow_status,
            cml_enabled=model.cml_enabled,
            cml_workspace_url=model.cml_workspace_url,
            cml_api_key_set=bool(model.cml_api_key),
            cml_project_name=model.cml_project_name,
            cml_status=model.cml_status,
            cdw_enabled=model.cdw_enabled,
            cdw_jdbc_url=model.cdw_jdbc_url,
            cdw_username=model.cdw_username,
            cdw_password_set=bool(model.cdw_password),
            cdw_status=model.cdw_status,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


# ============================================
# AI Analysis Schemas
# ============================================

class AIInsightBase(BaseModel):
    insight_id: str
    insight_type: str  # pattern_detected, anomaly_forecast, root_cause, optimization, capacity_warning, degradation_trend
    severity: str  # info, warning, critical
    title: str
    description: str
    recommendation: str
    confidence: float = Field(ge=0, le=1)
    affected_node_ids: List[str] = []
    related_alert_ids: List[str] = []
    metadata: Optional[dict] = None
    expires_at: Optional[datetime] = None


class AIInsightCreate(AIInsightBase):
    pass


class AIInsight(AIInsightBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AIInsightListResponse(BaseModel):
    total: int
    items: List[AIInsight]
    generated_at: datetime


class AIAlertAnalysisBase(BaseModel):
    analysis_id: str
    alert_id: str
    node_id: str
    summary: str
    root_cause: str
    recommendations: List[str]
    confidence: float = Field(ge=0, le=1)
    reasoning: Optional[str] = None
    should_execute_autonomously: bool = False
    urgency_score: int = Field(default=5, ge=1, le=10)
    sensor_data_used: Optional[dict] = None


class AIAlertAnalysisCreate(AIAlertAnalysisBase):
    pass


class AIAlertAnalysis(AIAlertAnalysisBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AIAlertAnalysisListResponse(BaseModel):
    total: int
    items: List[AIAlertAnalysis]


class AIActionStepSchema(BaseModel):
    step_number: int
    action_type: str
    description: str
    parameters: Optional[dict] = None
    estimated_duration_seconds: int = 30
    status: str = "pending"  # pending, executing, completed, failed, skipped
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[str] = None


class AIActionPlanBase(BaseModel):
    plan_id: str
    alert_id: str
    node_id: str
    analysis_id: Optional[str] = None
    root_cause: str
    priority: str  # low, medium, high, critical
    status: str  # pending, executing, completed, failed, cancelled
    steps: List[AIActionStepSchema]
    current_step_index: int = 0
    execution_log: Optional[List[dict]] = None
    failure_reason: Optional[str] = None
    success: Optional[bool] = None
    created_actions: Optional[List[str]] = None


class AIActionPlanCreate(AIActionPlanBase):
    pass


class AIActionPlan(AIActionPlanBase):
    id: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AIActionPlanListResponse(BaseModel):
    total: int
    items: List[AIActionPlan]


class AIStatusResponse(BaseModel):
    enabled: bool
    insights_count: int
    active_analyses: int
    pending_plans: int
    executing_plans: int
    completed_plans_24h: int
    failed_plans_24h: int
    last_insight_generation: Optional[datetime] = None
    last_analysis: Optional[datetime] = None


# ============================================
# Weather Schemas
# ============================================

class WeatherRegionSummary(BaseModel):
    region: str
    node_count: int
    conditions: dict
    avg_temperature: Optional[float] = None
    avg_wind_speed: Optional[float] = None
    avg_precipitation: Optional[float] = None
    avg_weather_impact: float = 0.0
    nodes_with_impact: int = 0


class WeatherSummaryResponse(BaseModel):
    timestamp: datetime
    total_nodes_with_weather: int
    nodes_with_significant_impact: int
    weather_conditions_summary: dict
    regions: List[WeatherRegionSummary]
    extreme_weather_nodes: List[str] = []
    avg_global_impact: float = 0.0


class NodeWeatherResponse(BaseModel):
    node_id: str
    weather_conditions: Optional[str] = None
    weather_impact: Optional[float] = None
    temperature_outdoor: Optional[float] = None
    precipitation_mm: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    last_updated: Optional[datetime] = None


# ============================================
# SLA Configuration Schemas
# ============================================

class SLAConfigBase(BaseModel):
    # Availability SLAs
    uptime_target_percent: float = 99.9
    max_outage_duration_minutes: int = 30
    max_monthly_downtime_minutes: int = 43

    # Latency SLAs
    max_latency_ms: float = 30.0
    latency_p95_target_ms: float = 20.0
    latency_p99_target_ms: float = 50.0

    # Quality SLAs (cable-specific)
    min_ds_snr_db: float = 33.0
    min_us_snr_db: float = 25.0
    max_packet_loss_percent: float = 0.5
    min_throughput_mbps: float = 100.0
    max_fec_uncorrected_rate: float = 0.01

    # Response SLAs
    critical_response_minutes: int = 15
    warning_response_minutes: int = 60
    resolution_target_hours: int = 4

    # Financial Parameters
    revenue_per_subscriber_per_hour: float = 0.15
    cost_per_outage_minute: float = 500.0
    sla_breach_penalty_percent: float = 10.0

    # Alerting Thresholds
    warning_threshold_percent: float = 90.0
    critical_threshold_percent: float = 95.0


class SLAConfigCreate(SLAConfigBase):
    pass


class SLAConfigUpdate(BaseModel):
    uptime_target_percent: Optional[float] = None
    max_outage_duration_minutes: Optional[int] = None
    max_monthly_downtime_minutes: Optional[int] = None
    max_latency_ms: Optional[float] = None
    latency_p95_target_ms: Optional[float] = None
    latency_p99_target_ms: Optional[float] = None
    min_ds_snr_db: Optional[float] = None
    min_us_snr_db: Optional[float] = None
    max_packet_loss_percent: Optional[float] = None
    min_throughput_mbps: Optional[float] = None
    max_fec_uncorrected_rate: Optional[float] = None
    critical_response_minutes: Optional[int] = None
    warning_response_minutes: Optional[int] = None
    resolution_target_hours: Optional[int] = None
    revenue_per_subscriber_per_hour: Optional[float] = None
    cost_per_outage_minute: Optional[float] = None
    sla_breach_penalty_percent: Optional[float] = None
    warning_threshold_percent: Optional[float] = None
    critical_threshold_percent: Optional[float] = None


class SLAConfig(SLAConfigBase):
    id: int
    config_key: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SLABreachBase(BaseModel):
    node_id: Optional[str] = None
    region: Optional[str] = None
    breach_type: str  # uptime, latency, quality, response
    metric_name: str
    sla_target: float
    actual_value: float
    severity: str  # warning, breach
    breach_start: datetime
    breach_end: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    affected_users: int = 0
    affected_nodes: int = 1
    financial_impact: float = 0.0
    resolved: bool = False
    resolution_notes: Optional[str] = None
    related_alert_ids: Optional[List[str]] = None
    related_action_ids: Optional[List[str]] = None


class SLABreach(SLABreachBase):
    id: int
    breach_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SLABreachListResponse(BaseModel):
    total: int
    items: List[SLABreach]


class SLAStatusResponse(BaseModel):
    config: SLAConfig
    current_uptime_percent: float
    monthly_downtime_minutes: float
    current_latency_avg_ms: float
    current_ds_snr_avg: float
    current_us_snr_avg: float
    active_breaches: int
    warning_alerts: int
    breaches_this_month: int
    total_penalty_exposure: float
    status: str  # healthy, warning, breach


# ============================================
# Financial Impact Schemas
# ============================================

class FinancialImpactBase(BaseModel):
    event_type: str  # alert, outage, degradation, maintenance
    event_id: Optional[str] = None
    node_id: Optional[str] = None
    region: Optional[str] = None
    impact_type: str  # revenue_loss, cost_avoidance, penalty, savings
    category: str  # outage, degradation, sla_breach, self_healing
    gross_impact: float
    mitigated_amount: float = 0.0
    net_impact: float
    affected_users: int = 0
    duration_minutes: int = 0
    calculation_method: Optional[str] = None
    calculation_details: Optional[dict] = None
    event_timestamp: datetime
    resolved_timestamp: Optional[datetime] = None


class FinancialImpact(FinancialImpactBase):
    id: int
    impact_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class FinancialImpactListResponse(BaseModel):
    total: int
    items: List[FinancialImpact]


class FinancialSummaryBase(BaseModel):
    period_type: str  # daily, weekly, monthly
    period_start: datetime
    period_end: datetime
    region: Optional[str] = None
    total_revenue_at_risk: float = 0.0
    actual_revenue_loss: float = 0.0
    revenue_protected: float = 0.0
    operational_costs: float = 0.0
    sla_penalties: float = 0.0
    ai_savings: float = 0.0
    total_incidents: int = 0
    auto_resolved_incidents: int = 0
    manual_interventions: int = 0
    avg_resolution_time_minutes: float = 0.0
    uptime_percent: float = 100.0
    sla_breaches: int = 0
    near_breaches: int = 0


class FinancialSummary(FinancialSummaryBase):
    id: int
    summary_id: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Digital Twin / Simulation Schemas
# ============================================

class SimulationScenarioBase(BaseModel):
    name: str
    description: Optional[str] = None
    scenario_type: str  # node_failure, plant_damage, capacity, maintenance, weather
    target_nodes: Optional[List[str]] = None
    target_regions: Optional[List[str]] = None
    target_percentage: Optional[float] = None
    parameters: dict
    duration_minutes: int = 60


class SimulationScenarioCreate(SimulationScenarioBase):
    pass


class SimulationScenario(SimulationScenarioBase):
    id: int
    scenario_id: str
    status: str
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SimulationScenarioListResponse(BaseModel):
    total: int
    items: List[SimulationScenario]


class SimulationResultBase(BaseModel):
    scenario_id: str
    simulation_start: datetime
    simulation_end: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    baseline_metrics: dict
    simulated_metrics: dict
    affected_nodes: List[str]
    affected_node_count: int = 0
    affected_customers_estimated: int = 0
    affected_regions: Optional[List[str]] = None
    cascading_failures: Optional[List[str]] = None
    neighbor_overload: Optional[List[str]] = None
    projected_revenue_loss: float = 0.0
    projected_sla_breaches: int = 0
    projected_penalty_cost: float = 0.0
    estimated_recovery_time_minutes: Optional[int] = None
    recommended_actions: Optional[List[dict]] = None
    risk_score: int = 0
    executive_summary: Optional[str] = None


class SimulationResult(SimulationResultBase):
    id: int
    result_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class SimulationResultListResponse(BaseModel):
    total: int
    items: List[SimulationResult]


class RunSimulationRequest(BaseModel):
    scenario_id: Optional[str] = None
    scenario_type: Optional[str] = None
    target_nodes: Optional[List[str]] = None
    target_regions: Optional[List[str]] = None
    target_count: Optional[int] = None
    parameters: Optional[dict] = None

    # Extended simulation parameters
    region: Optional[str] = None
    time_of_day: Optional[str] = "normal"  # peak, normal, off_peak
    node_types: Optional[List[str]] = None  # ["N+0", "N+1", "N+2", "N+3"]
    cascading_failure: bool = False
    recovery_strategy: Optional[str] = "manual"  # manual, ai_assisted
    custom_sla_uptime: Optional[float] = 99.9
    custom_sla_latency: Optional[float] = 30.0

    # Network connectivity parameters
    plant_capacity_percent: Optional[float] = 100.0
    headend_latency_ms: Optional[float] = 0.0
    network_congestion_factor: Optional[float] = 1.0
    packet_loss_percent: Optional[float] = 0.0


class SimulationComparisonResponse(BaseModel):
    scenario: SimulationScenario
    result: SimulationResult
    comparison: dict
    impact_summary: dict


class HistoricalBaselines(BaseModel):
    kpi_baselines: dict
    incident_baselines: dict
    network_baselines: dict
    period_hours: int
    calculated_at: str


class SimilarHistoricalIncident(BaseModel):
    action_id: str
    action_type: str
    node_id: str
    duration_minutes: float
    effectiveness_score: Optional[float] = None
    timestamp: Optional[str] = None
    outcome: str  # success, failed


class SimulationHistoricalContext(BaseModel):
    baselines: HistoricalBaselines
    similar_incidents: List[SimilarHistoricalIncident]
    alert_patterns: dict
    data_availability: dict
    confidence_score: float


# ============================================
# Executive Dashboard Schemas
# ============================================

class KPITrendPoint(BaseModel):
    timestamp: str
    ds_snr_db: float
    us_snr_db: float
    downstream_throughput_mbps: float
    upstream_throughput_mbps: float
    latency_ms: float
    packet_loss_percent: float
    active_modems: float
    node_cpu_utilization: float
    node_memory_utilization: float
    node_temperature: float
    sample_count: int


class PeriodComparisonMetric(BaseModel):
    metric_name: str
    current_value: float
    previous_value: float
    change_percent: float
    trend: str  # improving, stable, declining


class ExecutiveInsight(BaseModel):
    id: str
    type: str
    severity: str
    title: str
    description: str
    recommendation: str
    details: Optional[dict] = None


class ExecutiveSummaryResponse(BaseModel):
    timestamp: datetime
    period: str  # realtime, daily, weekly, monthly
    period_hours: Optional[int] = None

    # Network Health
    total_nodes: int
    healthy_nodes: int
    degraded_nodes: int
    outage_nodes: int
    maintenance_nodes: int
    network_uptime_percent: float

    # Subscriber Metrics
    total_subscribers: int = 0
    active_subscribers: int = 0
    avg_nps_score: Optional[float] = None
    churn_rate_percent: Optional[float] = None

    # SLA Status
    sla_compliance_percent: float
    active_sla_breaches: int
    near_breach_warnings: int
    breaches_this_period: int

    # Financial Summary
    revenue_at_risk: float
    revenue_protected: float
    actual_revenue_loss: float
    ai_cost_savings: float
    sla_penalty_exposure: float
    net_financial_impact: float
    historical_revenue_loss: Optional[float] = None

    # Incident Summary
    total_alerts: int
    critical_alerts: int
    warning_alerts: int
    auto_resolved: int
    manual_interventions: int
    avg_resolution_time_minutes: float
    mttr_minutes: Optional[float] = None

    # Performance Metrics
    avg_latency_ms: float
    avg_ds_snr_db: float = 0.0
    avg_us_snr_db: float = 0.0
    downstream_throughput_mbps: float = 0.0
    upstream_throughput_mbps: float = 0.0
    affected_subscribers_current: int = 0

    # Regional Breakdown
    regions: List[dict]

    # Top Issues
    top_issues: List[dict]

    # Trends
    trend_uptime: str  # improving, stable, declining
    trend_incidents: str
    trend_revenue_impact: str

    # Historical Trend Data for Charts
    kpi_trend_data: Optional[List[KPITrendPoint]] = None
    period_comparison: Optional[List[PeriodComparisonMetric]] = None

    # AI-generated insights
    ai_insights: Optional[List[ExecutiveInsight]] = None
    llm_analysis: Optional[dict] = None
    data_source: Optional[str] = None

    # Maintenance Compliance
    maintenance_compliance_percent: Optional[float] = None
    active_maintenance_windows: int = 0
    completed_maintenance_this_period: int = 0


class ExecutiveKPIResponse(BaseModel):
    network_availability: float
    mean_time_to_repair_minutes: float
    self_healing_success_rate: float
    customer_impact_score: float
    financial_efficiency: float
    sla_compliance: float
    subscriber_satisfaction_score: float = 0.0


# ============================================
# Agentic Capacity Planning Schemas
# ============================================

class AgentThought(BaseModel):
    id: str
    timestamp: str
    agent_id: str
    agent_name: str
    type: str  # thought, action, tool_call, tool_result, data, analysis, error
    content: str
    progress_percent: Optional[float] = None
    data_summary: Optional[dict] = None


class UpgradeImpactAnalysis(BaseModel):
    nodes_analyzed: int
    current_total_bandwidth_gbps: float
    projected_total_bandwidth_gbps: float
    bandwidth_improvement_percent: float
    current_avg_latency_ms: float
    projected_avg_latency_ms: float
    latency_improvement_percent: float
    nodes_by_current_type: dict  # N+0, N+1, etc.
    upgrade_target: str
    subscribers_to_benefit: int


class HardwareCompatibilityReport(BaseModel):
    total_nodes_checked: int
    compatible_count: int
    partial_upgrade_count: int
    replacement_count: int
    compatibility_by_manufacturer: dict
    estimated_total_cost: float
    estimated_upgrade_cost: float
    estimated_replacement_cost: float
    cost_breakdown_by_manufacturer: dict
    installation_timeline_days: int


class ComponentStatus(BaseModel):
    component_id: str
    component_type: str  # CMTS, Headend, Hub, Node
    name: str
    status: str
    utilization_percent: float
    capacity_current: float
    capacity_max: float
    performance_score: float
    issues: List[str]
    upgrade_priority: str  # low, medium, high, critical
    recommended_action: str
    estimated_cost: float
    trend_direction: str = "unknown"
    growth_rate_per_week: float = 0.0
    growth_rate_per_month: float = 0.0
    avg_utilization_7d: float = 0.0
    avg_utilization_30d: float = 0.0
    peak_utilization_7d: float = 0.0
    projected_days_to_threshold: Optional[int] = None
    performance_trend: str = "stable"


class HeadendComponentAnalysis(BaseModel):
    headend_id: str
    headend_name: str
    total_components: int
    components_by_type: dict
    components: List[dict]
    overall_health_score: float
    critical_issues: List[str]
    upgrade_recommendations: List[dict]
    estimated_total_upgrade_cost: float
    priority_upgrades: List[str]
    sites: List[dict] = []
    issues_by_location: dict = {}
    components_by_location: dict = {}
    health_by_location: dict = {}
    growth_by_location: dict = {}


class AgenticCapacityPlanningRequest(BaseModel):
    analysis_mode: str = Field(
        default="current_state",
        description="Analysis mode: current_state, upgrade_scenario, or add_redundancy"
    )
    target_upgrade_type: Optional[str] = Field(
        default=None,
        description="Target upgrade type: docsis_upgrade, node_split, cmts_expansion, fttp_migration"
    )
    current_node_type_filter: Optional[List[str]] = Field(
        default=None,
        description="Filter nodes by type: N+0, N+1, N+2, N+3"
    )
    region: Optional[str] = Field(
        default=None,
        description="Filter by service area region"
    )
    city: Optional[str] = Field(
        default=None,
        description="Filter by city"
    )
    headend_ids: Optional[List[str]] = Field(
        default=None,
        description="List of specific headend IDs to analyze"
    )
    node_ids: Optional[List[str]] = Field(
        default=None,
        description="List of specific node IDs to analyze"
    )
    include_nodes: bool = Field(
        default=True,
        description="Include nodes in the analysis"
    )
    include_headends: bool = Field(
        default=True,
        description="Include headends in the analysis"
    )
    include_cost_estimate: bool = Field(
        default=True,
        description="Include hardware compatibility and cost estimates"
    )
    forecast_periods: Optional[List[int]] = Field(
        default=None,
        description="Custom forecast periods in days (e.g., [30, 60, 90, 180])"
    )


class AgenticCapacityPlanningStartResponse(BaseModel):
    execution_id: str
    status: str


class AgenticCapacityPlanningStatus(BaseModel):
    execution_id: str
    status: str  # pending, running, completed, failed
    started_at: str
    completed_at: Optional[str] = None
    current_agent: Optional[str] = None
    current_agent_name: Optional[str] = None
    progress_percent: float = 0.0
    thoughts: List[AgentThought] = []
    analysis_mode: str = "current_state"
    target_upgrade_type: Optional[str] = None
    upgrade_analysis: Optional[UpgradeImpactAnalysis] = None
    hardware_compatibility: Optional[HardwareCompatibilityReport] = None
    headend_analysis: Optional[HeadendComponentAnalysis] = None
    result: Optional[dict] = None
    error: Optional[str] = None


# ============================================
# Sentiment Analytics Schemas
# ============================================

class SentimentAnalyticsResponse(BaseModel):
    """Aggregate sentiment analytics by node or service area"""
    avg_sentiment_score: float
    avg_nps_score: float
    total_responses: int
    sentiment_distribution: dict  # positive/neutral/negative/very_negative counts
    top_topics: List[dict]  # [{topic, count, avg_sentiment}]
    trend_7d: str  # improving, stable, declining
    by_source: dict  # {source: {count, avg_score}}
    proactive_outreach_needed: bool = False
    at_risk_accounts: int = 0


class CustomerModemHealth(BaseModel):
    """Modem health diagnostics for a customer"""
    account_id: str
    modem_mac: str
    modem_model: str
    docsis_version: str
    online: bool
    uptime_hours: float
    ds_power_level: Optional[float] = None
    us_power_level: Optional[float] = None
    ds_snr: Optional[float] = None
    us_snr: Optional[float] = None
    connection_drops_24h: int
    flap_count_24h: int = 0
    actual_download_mbps: float
    actual_upload_mbps: float
    provisioned_download_mbps: int
    provisioned_upload_mbps: int
    speed_delivery_ratio: float  # actual/provisioned
    health_score: float  # 0-100
    issues: List[str] = []


# ============================================
# Network Configuration Management Schemas
# ============================================

class NetworkDeviceBase(BaseModel):
    device_id: str
    device_type: str  # firewall, switch, router, modem
    device_role: Optional[str] = None
    hostname: str
    description: Optional[str] = None
    headend_id: Optional[str] = None
    hub_id: Optional[str] = None
    node_id: Optional[str] = None
    region: Optional[str] = None
    manufacturer: Optional[str] = None
    hardware_model: Optional[str] = None
    serial_number: Optional[str] = None
    firmware_version: Optional[str] = None
    os_version: Optional[str] = None
    management_ip: Optional[str] = None
    interfaces: Optional[list] = None
    uplink_speed_gbps: Optional[float] = None
    status: Optional[str] = "operational"
    uptime_seconds: Optional[int] = None
    running_config: Optional[dict] = None
    startup_config: Optional[dict] = None
    config_hash: Optional[str] = None
    compliance_status: Optional[str] = "compliant"
    cpu_utilization: Optional[float] = None
    memory_utilization: Optional[float] = None
    temperature_celsius: Optional[float] = None


class NetworkDeviceCreate(NetworkDeviceBase):
    pass


class NetworkDevice(NetworkDeviceBase):
    id: int
    last_seen: Optional[datetime] = None
    last_config_change: Optional[datetime] = None
    last_config_backup: Optional[datetime] = None
    last_compliance_scan: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NetworkDeviceListResponse(BaseModel):
    total: int
    devices: List[NetworkDevice]


class NetworkDeviceSummary(BaseModel):
    total_devices: int
    by_type: dict
    by_status: dict
    compliance_rate: float
    drift_count: int
    recent_changes: int


class ConfigTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    device_type: str
    device_role: Optional[str] = None
    config_template: dict
    version: str = "1.0"
    is_active: bool = True


class ConfigTemplateCreate(ConfigTemplateBase):
    pass


class ConfigTemplate(ConfigTemplateBase):
    id: int
    template_id: str
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConfigTemplateListResponse(BaseModel):
    total: int
    templates: List[ConfigTemplate]


class ConfigChangeLogBase(BaseModel):
    device_id: str
    change_request_id: Optional[str] = None
    change_type: str  # manual, automated, rollback, compliance_fix
    change_description: Optional[str] = None
    config_before: Optional[dict] = None
    config_after: Optional[dict] = None
    config_diff: Optional[dict] = None
    status: str = "applied"
    applied_by: Optional[str] = None
    change_timestamp: datetime
    rollback_available: bool = True
    rollback_deadline: Optional[datetime] = None


class ConfigChangeLog(ConfigChangeLogBase):
    id: int
    change_id: str
    rolled_back_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConfigChangeLogListResponse(BaseModel):
    total: int
    changes: List[ConfigChangeLog]


class ConfigComplianceBase(BaseModel):
    device_id: str
    template_id: Optional[str] = None
    compliance_status: str  # compliant, drifted, non_compliant
    severity: str = "low"
    drift_details: Optional[list] = None
    drift_count: int = 0
    scan_timestamp: datetime


class ConfigCompliance(ConfigComplianceBase):
    id: int
    compliance_id: str
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConfigComplianceListResponse(BaseModel):
    total: int
    items: List[ConfigCompliance]


class ChangeRequestBase(BaseModel):
    title: str
    description: Optional[str] = None
    change_type: str  # security, optimization, compliance, maintenance
    target_devices: list
    device_count: int = 0


class ChangeRequestCreate(ChangeRequestBase):
    requested_by: Optional[str] = None


class ChangeRequestUpdate(BaseModel):
    status: Optional[str] = None
    reviewed_by: Optional[str] = None
    approved_by: Optional[str] = None
    failure_reason: Optional[str] = None


class ChangeRequest(ChangeRequestBase):
    id: int
    request_id: str
    ai_risk_assessment: Optional[str] = None
    ai_impact_score: Optional[float] = None
    ai_recommendation: Optional[str] = None
    status: str = "pending_review"
    requested_by: Optional[str] = None
    reviewed_by: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    execution_started_at: Optional[datetime] = None
    execution_completed_at: Optional[datetime] = None
    execution_log: Optional[list] = None
    failure_reason: Optional[str] = None
    rollback_available: bool = False
    rollback_deadline: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChangeRequestListResponse(BaseModel):
    total: int
    requests: List[ChangeRequest]
