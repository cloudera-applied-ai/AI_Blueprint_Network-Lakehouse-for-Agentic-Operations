# Backend API Endpoints & Data Generation Documentation

This document provides a comprehensive overview of all API endpoints and the data generation mechanisms in the Network Data Lakehouse backend.

## Table of Contents
- [API Endpoints](#api-endpoints)
- [Data Generation Architecture](#data-generation-architecture)
- [Configuration Parameters](#configuration-parameters)

---

## API Endpoints

**Base URL:** `http://localhost:8000`
**API Docs:** `http://localhost:8000/docs` (Swagger UI)

### Root & Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Root endpoint with API information |
| GET | `/health` | Health check endpoint |

### System Control

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/system/status` | Get overall system status (data generation and LLM states) |
| POST | `/api/v1/system/pause` | Pause data generation and/or LLM queries |
| POST | `/api/v1/system/resume` | Resume data generation and/or LLM queries |
| GET | `/api/v1/system/llm-paused` | Check if LLM queries are paused |
| GET | `/api/v1/system/settings` | Get system-wide settings |
| POST | `/api/v1/system/settings` | Create or update system settings |

### Cell Towers

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/generate/towers` | Generate and store cell towers |
| GET | `/api/v1/towers` | List towers with pagination and filtering (region, status, manufacturer) |
| GET | `/api/v1/towers/{tower_id}` | Get specific tower by ID |
| GET | `/api/v1/towers/{tower_id}/equipment` | Get equipment details for a tower |
| GET | `/api/v1/towers/{tower_id}/equipment/history` | Get equipment historical data |

### KPI Metrics

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/generate/kpis` | Generate KPI metrics for towers |
| POST | `/api/v1/generate/historical-kpis` | Generate historical KPI metrics (60+ days) |
| GET | `/api/v1/kpis` | Get KPI metrics with pagination and filtering |
| GET | `/api/v1/kpis/aggregated` | Get aggregated KPI data for charting |

### Alerts

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/generate/alerts` | Generate alerts for towers |
| GET | `/api/v1/alerts` | List alerts with pagination and filtering (severity, status, tower_id, time range) |

### Self-Healing Actions

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/generate/actions` | Generate self-healing actions |
| GET | `/api/v1/actions` | List self-healing actions with filtering |
| GET | `/api/v1/actions/status-summary` | Get summary of action statuses |
| POST | `/api/v1/actions/cleanup` | Manually trigger actions cleanup |

### Statistics

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/stats` | Get overall statistics (tower, KPI, alert, action counts) |

### Weather

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/weather/summary` | Get global weather summary with regional breakdown |
| GET | `/api/v1/weather/tower/{tower_id}` | Get current weather data for a tower |

### Background Generator Control

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/generator/status` | Get background data generator status |
| POST | `/api/v1/generator/start` | Start background data generator |
| POST | `/api/v1/generator/stop` | Stop background data generator |

### AI Optimization

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/ai-optimization` | Get AI optimization settings |
| PUT | `/api/v1/ai-optimization` | Update AI optimization settings |
| POST | `/api/v1/ai-optimization/clear-cache` | Clear all AI analysis caches |

### Data Retention

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/retention/status` | Get data retention status and statistics |
| POST | `/api/v1/retention/cleanup` | Manually trigger data cleanup |

### Slack Integration

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/slack/status` | Get Slack integration status |
| POST | `/api/v1/slack/test` | Send a test notification |
| POST | `/api/v1/slack/notify/alert` | Send an alert notification |
| POST | `/api/v1/slack/notify/action` | Send a self-healing action notification |
| POST | `/api/v1/slack/notify/sdn` | Send an SDN command notification |

### LLM Configuration

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/llm/config` | Get LLM configuration |
| POST | `/api/v1/llm/config` | Create or update LLM configuration |
| PATCH | `/api/v1/llm/config` | Partially update LLM configuration |
| DELETE | `/api/v1/llm/config` | Delete LLM configuration |

### LLM Queue Service

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/llm/queue/status` | Get LLM queue service status |
| GET | `/api/v1/llm/queue/job/{job_id}` | Get status of a specific LLM job |
| POST | `/api/v1/llm/queue/submit` | Submit a single LLM job |
| POST | `/api/v1/llm/complete` | Complete/finalize an LLM job |
| POST | `/api/v1/llm/batch/submit` | Submit a batch of LLM jobs |
| GET | `/api/v1/llm/batch/status` | Get LLM batch status |
| POST | `/api/v1/llm/batch/wait` | Wait for LLM batch completion |
| POST | `/api/v1/llm/batch/complete` | Complete a batch of LLM jobs |

### Cloudera Services

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/cloudera/services` | Get Cloudera services configuration |
| POST | `/api/v1/cloudera/services` | Create or update Cloudera services |
| PATCH | `/api/v1/cloudera/services` | Partially update Cloudera services |
| GET | `/api/v1/cloudera/services/status` | Get Cloudera services status |
| POST | `/api/v1/cloudera/services/test/{service_name}` | Test a specific Cloudera service |

### Core Network Elements

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/core-network/summary` | Get core network infrastructure summary |
| GET | `/api/v1/core-network/data-centers` | List data centers |
| GET | `/api/v1/core-network/mscs` | List MSCs (Mobile Switching Centers) |
| GET | `/api/v1/core-network/sgws` | List SGWs (Serving Gateways) |
| GET | `/api/v1/core-network/pgws` | List PGWs (PDN Gateways) |
| GET | `/api/v1/core-network/mmes` | List MMEs (Mobility Management Entities) |
| GET | `/api/v1/core-network/hlrs` | List HLRs (Home Location Registers) |
| GET | `/api/v1/core-network/smscs` | List SMSCs (Short Message Service Centers) |
| GET | `/api/v1/core-network/all` | Get all core network elements |

### AI Insights & Analysis

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/ai/insights` | Get AI insights with pagination |
| GET | `/api/v1/ai/status` | Get AI analysis system status |
| POST | `/api/v1/ai/analyze/{alert_id}` | Trigger AI analysis for a specific alert |
| GET | `/api/v1/ai/analyses` | Get list of AI analyses |
| GET | `/api/v1/ai/analyses/{analysis_id}` | Get specific AI analysis details |
| GET | `/api/v1/ai/plans` | Get AI action plans |
| GET | `/api/v1/ai/plans/{plan_id}` | Get specific action plan details |
| POST | `/api/v1/ai/plans/{plan_id}/cancel` | Cancel an action plan |
| POST | `/api/v1/ai/analyze-and-execute/{alert_id}` | Analyze alert and execute remediation |

### SLA Management

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/sla/config` | Get SLA configuration |
| POST | `/api/v1/sla/config` | Create SLA configuration |
| PATCH | `/api/v1/sla/config` | Update SLA configuration |
| GET | `/api/v1/sla/status` | Get SLA status and metrics |
| GET | `/api/v1/sla/breaches` | Get SLA breach records |
| POST | `/api/v1/sla/breaches/{breach_id}/acknowledge` | Acknowledge an SLA breach |
| POST | `/api/v1/sla/breaches/{breach_id}/resolve` | Resolve an SLA breach |

### Financial Impact

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/financial/impacts` | Get financial impact records |
| GET | `/api/v1/financial/summary` | Get financial summary (revenue loss, costs) |

### Simulation

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/simulation/scenarios` | List simulation scenarios |
| POST | `/api/v1/simulation/scenarios` | Create a simulation scenario |
| POST | `/api/v1/simulation/run` | Run a simulation |
| GET | `/api/v1/simulation/results` | Get simulation results |
| GET | `/api/v1/simulation/compare` | Compare results against baseline |
| GET | `/api/v1/simulation/historical-context` | Get historical context |

### Executive Dashboard

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/executive/summary` | Get executive summary with KPIs, alerts, SLA metrics |
| GET | `/api/v1/executive/kpis` | Get executive-level KPI metrics and trends |

### Agent Studio Workflows

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/agent-studio/workflows` | List available multi-agent workflows |
| GET | `/api/v1/agent-studio/workflows/{workflow_id}` | Get workflow configuration |
| POST | `/api/v1/agent-studio/execute` | Execute a workflow with natural language query |
| GET | `/api/v1/agent-studio/executions/{execution_id}` | Get execution status and results |

---

## Data Generation Architecture

### Overview

The backend generates simulated telecom network data through background tasks that run continuously when the system is active.

### Main Generation Loop

**File:** `application/backend/app/background_tasks.py`

#### Timing Intervals

| Task | Interval | Description |
|------|----------|-------------|
| KPI Generation | 30-second tick (`KPI_CYCLE_SECONDS`); each node sampled every 5 min (`KPI_GENERATION_INTERVAL_SECONDS`) | Generate metrics for a rotating slice of fiber nodes |
| Insights Generation | 30 seconds | Rule-based pattern detection |
| Weather Fetch | 5 minutes | Get live weather for tower locations |
| Data Rollups | Varies | 1min, 5min, hourly, daily aggregations |

### KPI Metrics Generation

Each 30-second tick generates **25+ metrics** for a rotating slice of ~724 of the **7,240 fiber nodes**, so every node is refreshed once per 5 minutes:

**Call Metrics:**
- Call setup success rate (92-99.5%)
- Call drop rate (0.1-5%)

**Network Quality:**
- Handover success rate (85-98%)
- RRC connection success rate (90-99%)

**Performance:**
- Latency (10-100ms)
- Packet loss (0.1-3%)
- Throughput (50-500 Mbps)

**Resource Utilization:**
- CPU usage (20-90%)
- Memory usage (30-85%)
- Temperature (20-75°C)

**Signal Metrics:**
- SINR, RSRP, RSRQ, CQI averages

**Data Volume (defaults: 7,240 nodes, one sample per node per 5 minutes):**
- ~1,450 KPI records per minute (~724 per 30-second tick)
- ~174k raw rows held (2-hour raw retention), ~2.5M rows across all tiers (~0.5 GB)
- Tunable via `KPI_GENERATION_INTERVAL_SECONDS`, `KPI_CYCLE_SECONDS`, `NODES_PER_HUB`, and the `RETENTION_*` env vars (see `config.py`)

### Weather Impact on KPIs

Weather conditions affect KPI values dynamically:

| Condition | Impact |
|-----------|--------|
| Rain | RSRP -15dBm, RSRQ -5dB, SINR -8dB, packet loss +4%, throughput -40% |
| Temperature | CPU +25%, equipment temp +20°C, thermal throttling at >70°C |
| Wind | Handover success -15%, call drops +3% |
| Overall | Call setup time +50%, success rate -10% |

### Alert Generation

**Probability:** 0.8% per node per KPI sample (~6 alerts per 30-second tick)

**Alert Types (11 total):**
- `CELL_OUTAGE`
- `DEGRADED_SERVICE`
- `HIGH_CALL_DROP`
- `CONGESTION`
- `EQUIPMENT_FAILURE`
- `HANDOVER_ISSUES`
- `HIGH_LATENCY`
- `PACKET_LOSS`
- `HIGH_CPU_USAGE`
- `HIGH_MEMORY_USAGE`
- `HIGH_TEMPERATURE`

**Severity Distribution:**
| Severity | Percentage | Tower Status Effect |
|----------|------------|---------------------|
| Critical | 20% | Tower status → "outage" |
| Warning | 50% | Tower status → "degraded" |
| Info | 30% | No status change |

**Weather Boost:** Alert probability multiplied by up to 3x during bad weather (impact > 0.3)

### Self-Healing Action Lifecycle

**Action Types:**
1. `LOAD_BALANCE` - Redistribute traffic
2. `PARAMETER_OPTIMIZATION` - Optimize RF parameters
3. `CELL_REBOOT` - Controlled restart
4. `TRAFFIC_REROUTING` - Reroute to neighbors
5. `ANTENNA_ADJUSTMENT` - Adjust tilt/azimuth
6. `TICKET_CREATION` - Manual intervention
7. `NEIGHBOR_CELL_EXPANSION` - Expand capacity

**State Machine:**

```
PENDING (t=0)
    ↓ [~15s, 20% chance per cycle]
IN_PROGRESS
    ↓ [~25-35s, 30% chance per cycle]
COMPLETED (90%) / FAILED (10%)
```

**On Completion:**
- **Success (90%):** Resolves alert, updates tower to healthy
- **Failure (10%):** Creates dispatch ticket for manual intervention

### AI Analysis & Cost Optimization

**Settings:**
| Parameter | Value | Description |
|-----------|-------|-------------|
| `llm_sample_rate` | 5 | Use LLM for 1 in 5 alerts (20%) |
| `tower_cooldown_minutes` | 15 | Skip re-analysis within 15 min |
| `cache_ttl_minutes` | 30 | Cache results for 30 minutes |
| `max_concurrent_analyses` | 5 | Max parallel AI tasks |

**Distribution:**
- 20% of alerts: Full LLM analysis (Claude API)
- 80% of alerts: Fast rule-based analysis

### Data Retention & Rollup

**File:** `application/backend/app/data_retention.py`

**Retention Policy:**

| Data Tier | Retention (default) | Env var |
|-----------|---------------------|---------|
| Raw (5 min per node) | 2 hours | `RETENTION_RAW_HOURS` |
| 1-minute | 6 hours | `RETENTION_1MIN_HOURS` |
| 5-minute | 12 hours | `RETENTION_5MIN_HOURS` |
| Hourly | 3 days | `RETENTION_HOURLY_DAYS` |
| Daily | 30 days | `RETENTION_DAILY_DAYS` |
| Resolved Alerts | 30 days | `RETENTION_RESOLVED_ALERTS_DAYS` |
| Completed Actions | 30 days | `RETENTION_COMPLETED_ACTIONS_DAYS` |

**Rollup Schedule:**

| Rollup | Frequency | Aggregation |
|--------|-----------|-------------|
| 1-min | Every 60s | 12 raw records → 1 |
| 5-min | Every 5 min | 5 × 1-min records → 1 |
| Hourly | Every hour | 12 × 5-min records → 1 |
| Daily | Every day | 24 × hourly records → 1 |

**Storage Efficiency:** ~97% reduction after rollup

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│         Every 30 s tick (each node every 5 min)          │
├─────────────────────────────────────────────────────────┤
│  1. Generate KPI metrics (~724-node slice × 25 metrics) │
│     - Apply weather effects                              │
│     - Bulk insert to KPIMetricsModel                    │
│                                                          │
│  2. Generate alerts (0.2% probability per tower)        │
│     - Set severity (20% CRITICAL, 50% WARNING)          │
│     - Update tower status                               │
│     - Send Slack notification (if critical)             │
│     - Trigger AI analysis task                          │
│                                                          │
│  3. Generate self-healing actions (1 per new alert)     │
│     - Set status = PENDING                              │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Action Processing Loop                      │
├─────────────────────────────────────────────────────────┤
│  PENDING → IN_PROGRESS (20% chance after 15s)           │
│  IN_PROGRESS → COMPLETED/FAILED (30% chance after 25s)  │
│  On completion: resolve alert, update tower status      │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Data Retention Service                      │
├─────────────────────────────────────────────────────────┤
│  - 1-min rollup (every 60s)                             │
│  - 5-min rollup (every 5 min)                           │
│  - Hourly rollup (every hour)                           │
│  - Daily rollup (every day)                             │
│  - Cleanup expired data (every 5 min)                   │
└─────────────────────────────────────────────────────────┘
```

---

## Configuration Parameters

**File:** `application/backend/app/config.py`

| Parameter | Default | Description |
|-----------|---------|-------------|
| `TOTAL_TOWERS` | 2000 | Total number of simulated towers |
| `KPI_GENERATION_INTERVAL_SECONDS` | 5 | KPI generation frequency |
| `ALERT_CHECK_INTERVAL_SECONDS` | 10 | Alert check frequency |
| `HEALING_ACTION_INTERVAL_SECONDS` | 15 | Action processing frequency |
| `DATABASE_URL` | `postgresql://telco_user:...@localhost:5432/telco_network` | PostgreSQL connection |

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| **Total API Endpoints** | 103+ |
| **Towers Simulated** | 2000 |
| **KPI Metrics per Tower** | 25+ |
| **KPI Records per Minute** | ~1,450 |
| **Expected Alerts per Hour** | ~1,440 |
| **Alert Types** | 11 |
| **Self-Healing Action Types** | 7 |
| **Action Success Rate** | 90% |
| **Data Retention (Raw)** | 2 hours |
| **Data Retention (Daily)** | 30 days |
