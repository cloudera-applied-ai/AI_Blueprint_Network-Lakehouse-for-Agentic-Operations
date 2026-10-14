# Packet Analysis & Edge Data Center Anomaly Flow

Integrated packet-capture network-security analysis (ported from the
`amp-telco-packetanalysis` accelerator) plus an edge data center anomaly flow,
built on this app's existing infrastructure — the LLM queue, PostgreSQL models,
`/api/v1` + `X-API-Key` routers, the thought-stream execution pattern, and the
React dashboard.

## What it does

**Packet Analysis tab** — upload a `.pcap`; scapy parses it, GeoIP + threat-intel
enrich it, and four network agents (Threat Detection, Protocol Analysis,
Behavior Analysis, Forensics) analyze it in parallel through the shared LLM
queue. Chat over the capture and export a Markdown or Word (`.docx`) report.

**Edge Operations tab** — pick a **headend** (the NOC's data-center entity) and a
scenario (port scan, C2 beacon, data exfiltration, DDoS). The headend's local
model runs a scripted detect/contain **thought-stream**, then stages a suspect
pcap to **S3** (configurable endpoint — AWS S3 / Ozone / MinIO; automatic
local-disk fallback). The primary-DC **poller** retrieves it and runs the same
four agents; the resulting analysis links back to that headend and appears in
Packet Analysis with an edge-context banner.

## Where things live

- Backend capability: `application/backend/app/pcap/` (parser, geoip,
  threat_intel, agents, analysis, report, docx_report; `llm_bridge.py` routes
  the agents through `llm_queue`).
- Edge simulation: `application/backend/app/edge/` (scenarios, synthesizer,
  staging, engine, poller). Committed synthetic fixtures:
  `app/pcap/fixtures/*.pcap` — regenerate with the synthesizer; no real traffic.
- Routes: `app/routes/pcap.py`, `app/routes/edge.py` (mounted in `main.py`).
  S3 staging test: `POST /api/v1/cloudera/services/test/s3`.
- Models: `PcapAnalysisModel`, `EdgeAnomalyExecutionModel`,
  `PcapChatMessageModel`, plus `s3_staging_*` fields on `ClouderaServicesModel`.
- Frontend: `src/components/dashboard/{PacketAnalysisView,EdgeOperationsView}.tsx`,
  `src/services/api/{packetApi,edgeApi}.ts`, `src/types/{packet,edge}.ts`. S3
  config lives in the Cloudera Services panel.

S3 staging config is read from the `cloudera_services` row (the same panel that
holds the Iceberg warehouse), so captures stage to whatever object store the
lakehouse uses.

## Testing — all in Docker (no local installs)

Run the whole stack:

```bash
docker compose up -d --build      # postgres + backend + frontend (nginx :8100)
curl http://localhost:8000/health
```

Run the backend test suite in a throwaway container (the suite uses in-memory
sqlite; `tests/` is `.dockerignore`d out of the image, so bind-mount it):

```bash
docker compose run --rm --no-deps \
  -v "$PWD/application/backend:/app" -w /app backend \
  pytest -q
```

Frontend typecheck + build in a Node container (no host npm install):

```bash
docker run --rm -v "$PWD/application:/app" -w /app node:22-slim \
  sh -c "npm ci && npm run build"
```

End-to-end edge flow against the running stack:

```bash
K="X-API-Key: dev-api-key-change-me"; B="http://localhost:8000/api/v1"
HID=$(curl -s -H "$K" "$B/headends?limit=1" | python3 -c "import sys,json;print(json.load(sys.stdin)['items'][0]['headend_id'])")
EID=$(curl -s -H "$K" -H "Content-Type: application/json" \
  -d "{\"headend_id\":\"$HID\",\"scenario_id\":\"port_scan\"}" \
  $B/edge/events | python3 -c "import sys,json;print(json.load(sys.stdin)['execution_id'])")
# poll $B/edge/events/$EID until status == staged, then:
curl -s -H "$K" -X POST $B/edge/poll                       # -> {"processed": 1}
# the linked analysis_id now has source=edge + edge_context
```

Without an LLM configured the scripted edge thought-stream still completes and
the agents degrade to graceful stubs; the `.docx` report falls back to
structured-only content. Configure a provider under Settings for full AI
analysis.

## Two-model mode (security analyst + generalist writer)

The agents support a two-model split, which pairs a **security-domain model**
with a **generalist writer**:

- **Model Name** (analyst) — a security model such as **Cisco Foundation-Sec-8B**
  handles detection and emits structured findings. The framework's JSON-repair
  and anti-hallucination validators (`pcap/agents/base.py`) exist precisely for
  small security models that struggle with strict JSON.
- **Writer Model** (optional) — a generalist such as **Qwen** writes the analysis
  prose, the report, and the chat replies.

Set both in **Settings → AI**. Leave *Writer Model* blank for single-model mode
(the analyst produces prose too).

The writer's transport is **all-or-nothing** (no per-field mixing):

- ***Writer Endpoint URL* blank — same-endpoint mode.** Both models are served
  from the analyst's provider/endpoint/credentials; only the model name differs
  (e.g. one Ollama endpoint serving `foundation-sec:8b` + `qwen2.5`). *Writer
  Provider* / *Writer API Key* are ignored in this mode, so a partial writer
  block can't produce an unauthenticated or misrouted request. Note this only
  works on multi-model servers such as Ollama — a Cloudera AI Inference
  endpoint serves a **single** model and will reject a second model name.
- ***Writer Endpoint URL* set — separate-endpoint mode.** The writer uses
  *Writer Provider* (or the analyst's provider if blank) and *Writer API Key*.
  If no writer key is given, the analyst's JWT is reused as the Bearer token
  (CDP JWTs are valid across CAI Inference endpoints in the same environment);
  for Ollama no auth is sent. So the analyst can run on a Cloudera AI Inference
  endpoint while the writer runs on a separate Ollama (or a second CAI
  endpoint). Fully on-prem, no external API.

Use the **Test Writer Model** button under the writer fields (or
`POST /api/v1/llm/test-connection` with `{"role": "writer"}`) to probe the
writer's endpoint/auth through the real queue path before running an analysis.

Wiring: `LLMConfigModel.{writer_model_name, writer_provider, writer_endpoint_url,
writer_api_key}`; `pcap/llm_bridge.py` builds the writer request via
`_EffectiveConfig` (semantics above), routes the `writer` role to it and the
`analyst` role to the primary config; `base.py::run_agent` runs analyst
findings-only + writer prose when a writer is configured, and falls back to a
single model otherwise.
