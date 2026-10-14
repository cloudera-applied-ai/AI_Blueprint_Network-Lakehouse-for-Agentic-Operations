/**
 * Packet-capture analysis API (manual upload + chat + reports).
 */
import { apiRequest, getApiBaseUrl } from './baseClient';
import type {
  CaptureResponse,
  CaptureSummary,
  PcapChatMessage,
} from '../../types/packet';

function apiKey(): string {
  return import.meta.env.VITE_API_KEY || 'dev-api-key-change-me';
}

/** Multipart upload — must NOT set Content-Type (browser sets the boundary). */
export async function analyzePcap(file: File): Promise<CaptureResponse> {
  const form = new FormData();
  form.append('file', file);
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 600_000); // agents can be slow
  try {
    const res = await fetch(`${getApiBaseUrl()}/api/v1/pcap/analyze`, {
      method: 'POST',
      headers: { 'X-API-Key': apiKey() },
      body: form,
      signal: controller.signal,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `Analyze failed: ${res.status}`);
    }
    return (await res.json()) as CaptureResponse;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function listCaptures(): Promise<CaptureSummary[]> {
  return apiRequest<CaptureSummary[]>('/pcap/captures');
}

export async function getCapture(captureId: string): Promise<CaptureResponse> {
  return apiRequest<CaptureResponse>(`/pcap/captures/${captureId}`);
}

export async function pcapChat(
  captureId: string,
  messages: PcapChatMessage[]
): Promise<{ reply: string }> {
  return apiRequest<{ reply: string }>(
    '/pcap/chat',
    { method: 'POST', body: JSON.stringify({ capture_id: captureId, messages }) },
    300_000
  );
}

export async function generatePcapReport(captureId: string): Promise<{ report_markdown: string }> {
  return apiRequest<{ report_markdown: string }>(
    '/pcap/report',
    { method: 'POST', body: JSON.stringify({ capture_id: captureId }) },
    300_000
  );
}

/** Fetch the server-generated .docx and trigger a browser download. */
export async function downloadPcapDocx(
  captureId: string,
  opts: { includeChat?: boolean; messages?: PcapChatMessage[] } = {}
): Promise<void> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/pcap/report/docx`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey() },
    body: JSON.stringify({
      capture_id: captureId,
      include_chat: opts.includeChat ?? false,
      messages: opts.messages,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Report failed: ${res.status}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `pcap-incident-report-${new Date().toISOString().split('T')[0]}.docx`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
