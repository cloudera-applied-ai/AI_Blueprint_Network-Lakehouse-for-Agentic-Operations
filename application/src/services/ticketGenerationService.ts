/**
 * Ticket Generation Service
 * Creates detailed field service tickets with hardware manual references
 * Used by AI agents and autonomous executor for crew dispatch
 */

import { hardwareManualService, TroubleshootingGuide, ManagementProcedure } from './hardwareManualService';
import { Alert, FiberNode, KPIMetrics } from '@/types';

export interface FieldServiceTicket {
  ticket_id: string;
  timestamp: Date;
  priority: 'critical' | 'high' | 'medium' | 'low';
  status: 'open' | 'assigned' | 'in_progress' | 'resolved' | 'closed';

  // Site Information
  node_id: string;
  site_id: string;
  site_location: {
    city: string;
    region: string;
    latitude: number;
    longitude: number;
    elevation_m: number;
  };
  site_access: {
    type: string;
    accessibility: string;
    special_instructions?: string;
  };

  // Problem Description
  issue_summary: string;
  issue_details: string;
  affected_services: string[];
  user_impact: string;
  sla_tier: string;

  // Equipment Information
  equipment: {
    manufacturer: string;
    model: string;
    firmware_version: string;
    baseband_version: string;
    serial_number?: string;
    warranty_status?: string;
  };

  // Hardware Manual References
  manual_references: {
    manual_id: string;
    troubleshooting_guide?: TroubleshootingGuide;
    recommended_procedures: ManagementProcedure[];
    vendor_support_contact: {
      phone: string;
      email: string;
      portal: string;
    };
  };

  // Diagnostic Information
  diagnostics: {
    recent_kpis: string[];
    environmental_factors: string[];
    sensor_readings: string[];
    related_alerts: string[];
  };

  // Work Instructions
  work_instructions: {
    estimated_time: string;
    required_skills: string[];
    required_tools: string[];
    safety_warnings: string[];
    step_by_step_procedure: string[];
    verification_steps: string[];
    rollback_procedure?: string[];
  };

  // Assignment
  assigned_to?: string;
  assigned_at?: Date;
  estimated_arrival?: Date;

  // Resolution
  resolution_notes?: string;
  resolved_at?: Date;
  resolved_by?: string;
  parts_used?: string[];
  actual_time_spent?: string;
}

class TicketGenerationService {
  /**
   * Generate comprehensive field service ticket
   */
  generateTicket(
    alert: Alert,
    node: FiberNode,
    recentKPIs: KPIMetrics[],
    aiAnalysis?: {
      rootCause: string;
      recommendations: string[];
      requiresSiteVisit: boolean;
      requiresVendorSupport: boolean;
      estimatedResolutionTime?: string;
    }
  ): FieldServiceTicket {
    const manual = hardwareManualService.getManual(node.manufacturer || '', node.hardware_model || '');
    const troubleshootingGuide = hardwareManualService.getTroubleshootingGuide(
      node.manufacturer || '',
      node.hardware_model || '',
      alert.description
    );

    const ticket_id = `FST-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
    const priority = this.determinePriority(alert, node);

    const ticket: FieldServiceTicket = {
      ticket_id,
      timestamp: new Date(),
      priority,
      status: 'open',

      node_id: node.node_id,
      site_id: node.node_id,
      site_location: {
        city: node.city || '',
        region: node.region,
        latitude: node.latitude,
        longitude: node.longitude,
        elevation_m: 0,
      },
      site_access: {
        type: node.node_type || 'N+0',
        accessibility: 'Standard',
        special_instructions: this.generateAccessInstructions(node),
      },

      issue_summary: alert.description,
      issue_details: this.generateIssueDetails(alert, node, aiAnalysis),
      affected_services: this.identifyAffectedServices(node, alert),
      user_impact: this.calculateUserImpact(node, alert),
      sla_tier: (node.homes_active && node.homes_active > 500) ? 'Critical' : 'Standard',

      equipment: {
        manufacturer: node.manufacturer || 'Unknown',
        model: node.hardware_model || 'Unknown',
        firmware_version: node.firmware_version || 'N/A',
        baseband_version: node.docsis_version || 'N/A',
        serial_number: `SN-${node.node_id.replace('NODE-', '')}`,
        warranty_status: 'In Warranty', // Simplified
      },

      manual_references: {
        manual_id: manual?.manual_id || 'N/A',
        troubleshooting_guide: troubleshootingGuide ?? undefined,
        recommended_procedures: this.selectRelevantProcedures(manual, alert, troubleshootingGuide ?? undefined),
        vendor_support_contact: manual ? manual.support_contact : {
          phone: 'N/A',
          email: 'N/A',
          portal: 'N/A',
        },
      },

      diagnostics: {
        recent_kpis: this.formatKPIsForTicket(recentKPIs),
        environmental_factors: this.identifyEnvironmentalFactors(node, alert),
        sensor_readings: [`Node Status: ${node.status}`, `Power Supply: ${node.power_supply_status || 'N/A'}`, `DOCSIS: ${node.docsis_version || 'N/A'}`],
        related_alerts: [alert.alert_id],
      },

      work_instructions: this.generateWorkInstructions(
        node,
        alert,
        troubleshootingGuide ?? undefined,
        manual,
        aiAnalysis
      ),
    };

    return ticket;
  }

  /**
   * Generate ticket in plain text format for field technician
   */
  formatTicketForFieldTech(ticket: FieldServiceTicket): string {
    return `
═══════════════════════════════════════════════════════════════════
                    FIELD SERVICE TICKET
═══════════════════════════════════════════════════════════════════

TICKET: ${ticket.ticket_id}
PRIORITY: ${ticket.priority.toUpperCase()}
CREATED: ${ticket.timestamp.toISOString()}
SLA TIER: ${ticket.sla_tier}

───────────────────────────────────────────────────────────────────
SITE INFORMATION
───────────────────────────────────────────────────────────────────
Node ID: ${ticket.node_id}
Site ID: ${ticket.site_id}
Location: ${ticket.site_location.city}, ${ticket.site_location.region}
Coordinates: ${ticket.site_location.latitude.toFixed(4)}, ${ticket.site_location.longitude.toFixed(4)}
Elevation: ${ticket.site_location.elevation_m}m

Site Access: ${ticket.site_access.type} (${ticket.site_access.accessibility})
${ticket.site_access.special_instructions ? `Special Instructions: ${ticket.site_access.special_instructions}` : ''}

───────────────────────────────────────────────────────────────────
PROBLEM DESCRIPTION
───────────────────────────────────────────────────────────────────
${ticket.issue_summary}

${ticket.issue_details}

Affected Services: ${ticket.affected_services.join(', ')}
User Impact: ${ticket.user_impact}

───────────────────────────────────────────────────────────────────
EQUIPMENT INFORMATION
───────────────────────────────────────────────────────────────────
Manufacturer: ${ticket.equipment.manufacturer}
Model: ${ticket.equipment.model}
Firmware: ${ticket.equipment.firmware_version}
Baseband: ${ticket.equipment.baseband_version}
Serial Number: ${ticket.equipment.serial_number}
Warranty: ${ticket.equipment.warranty_status}

───────────────────────────────────────────────────────────────────
HARDWARE MANUAL REFERENCE
───────────────────────────────────────────────────────────────────
Manual ID: ${ticket.manual_references.manual_id}

${ticket.manual_references.troubleshooting_guide ? `
Known Issue: ${ticket.manual_references.troubleshooting_guide.symptom}
Issue ID: ${ticket.manual_references.troubleshooting_guide.issue_id}

Possible Causes:
${ticket.manual_references.troubleshooting_guide.possible_causes.map((c, i) => `  ${i + 1}. ${c}`).join('\n')}

Diagnostic Steps:
${ticket.manual_references.troubleshooting_guide.diagnostic_steps.map((s, i) => `  ${i + 1}. ${s}`).join('\n')}

Resolution Steps:
${ticket.manual_references.troubleshooting_guide.resolution_steps.map((s, i) => `  ${i + 1}. ${s}`).join('\n')}

Estimated Resolution Time: ${ticket.manual_references.troubleshooting_guide.estimated_resolution_time}
` : 'No specific troubleshooting guide found.'}

Vendor Support:
  Phone: ${ticket.manual_references.vendor_support_contact.phone}
  Email: ${ticket.manual_references.vendor_support_contact.email}
  Portal: ${ticket.manual_references.vendor_support_contact.portal}

───────────────────────────────────────────────────────────────────
WORK INSTRUCTIONS
───────────────────────────────────────────────────────────────────
Estimated Time: ${ticket.work_instructions.estimated_time}

Required Skills: ${ticket.work_instructions.required_skills.join(', ')}

Required Tools:
${ticket.work_instructions.required_tools.map((t, i) => `  ${i + 1}. ${t}`).join('\n')}

⚠️  SAFETY WARNINGS:
${ticket.work_instructions.safety_warnings.map((w, i) => `  ${i + 1}. ${w}`).join('\n')}

PROCEDURE:
${ticket.work_instructions.step_by_step_procedure.map((s, i) => `  ${i + 1}. ${s}`).join('\n')}

VERIFICATION:
${ticket.work_instructions.verification_steps.map((s, i) => `  ${i + 1}. ${s}`).join('\n')}

${ticket.work_instructions.rollback_procedure ? `
ROLLBACK (if needed):
${ticket.work_instructions.rollback_procedure.map((s, i) => `  ${i + 1}. ${s}`).join('\n')}
` : ''}

───────────────────────────────────────────────────────────────────
DIAGNOSTIC DATA
───────────────────────────────────────────────────────────────────
Recent KPIs:
${ticket.diagnostics.recent_kpis.map(k => `  • ${k}`).join('\n')}

Environmental Factors:
${ticket.diagnostics.environmental_factors.map(f => `  • ${f}`).join('\n')}

Sensor Readings:
${ticket.diagnostics.sensor_readings.map(s => `  • ${s}`).join('\n')}

───────────────────────────────────────────────────────────────────
RECOMMENDED PROCEDURES (from manual)
───────────────────────────────────────────────────────────────────
${ticket.manual_references.recommended_procedures.map(proc => `
${proc.name} (${proc.procedure_id})
  Category: ${proc.category}
  Estimated Time: ${proc.estimated_time}
  Access Level Required: ${proc.required_access_level}
`).join('\n')}

═══════════════════════════════════════════════════════════════════
                        END OF TICKET
═══════════════════════════════════════════════════════════════════
`;
  }

  private determinePriority(alert: Alert, node: FiberNode): 'critical' | 'high' | 'medium' | 'low' {
    if (alert.severity === 'critical' || (node.homes_active && node.homes_active > 500)) {
      return 'critical';
    } else if (alert.severity === 'warning' && (node.homes_active && node.homes_active > 200)) {
      return 'high';
    } else if (alert.severity === 'warning') {
      return 'medium';
    }
    return 'low';
  }

  private generateAccessInstructions(node: FiberNode): string | undefined {
    const instructions: string[] = [];

    if (node.amplifier_cascade && node.amplifier_cascade > 5) {
      instructions.push('Extended plant - verify amplifier chain access');
    }
    if (node.coax_plant_miles && node.coax_plant_miles > 10) {
      instructions.push('Large service area - coordinate with field crew');
    }
    if (node.power_supply_status === 'partial_failure' || node.power_supply_status === 'critical') {
      instructions.push('Power supply issue detected - bring replacement units');
    }
    if (node.battery_backup_hours && node.battery_backup_hours < 2) {
      instructions.push('Low battery backup - prioritize power restoration');
    }

    return instructions.length > 0 ? instructions.join('; ') : undefined;
  }

  private generateIssueDetails(alert: Alert, _node: FiberNode, aiAnalysis?: any): string {
    let details = `Alert Type: ${alert.alert_type}\n`;
    details += `Severity: ${alert.severity}\n`;
    details += `Time Reported: ${alert.timestamp.toISOString()}\n\n`;

    if (aiAnalysis) {
      details += `AI Root Cause Analysis: ${aiAnalysis.rootCause}\n\n`;
      details += `AI Recommendations:\n${aiAnalysis.recommendations.map((r: string, i: number) => `  ${i + 1}. ${r}`).join('\n')}`;
    }

    return details;
  }

  private identifyAffectedServices(node: FiberNode, alert: Alert): string[] {
    const services = [];
    const docsis = node.docsis_version || '3.1';
    if (docsis === '4.0') services.push('DOCSIS 4.0 Service');
    else if (docsis === '3.1') services.push('DOCSIS 3.1 Service');
    else services.push('DOCSIS 3.0 Service');
    if (alert.alert_type === 'node_outage') services.push('Internet', 'Video', 'Voice');
    return services;
  }

  private calculateUserImpact(node: FiberNode, alert: Alert): string {
    const homesActive = node.homes_active || 350;
    if (alert.severity === 'critical') {
      return `HIGH - Up to ${homesActive} subscribers affected (${node.homes_passed || 500} homes passed)`;
    } else if (alert.severity === 'warning') {
      return `MEDIUM - Degraded service for approximately ${Math.floor(homesActive * 0.3)} subscribers`;
    }
    return 'LOW - Minimal subscriber impact';
  }

  private selectRelevantProcedures(manual: any, alert: Alert, _troubleshootingGuide?: TroubleshootingGuide): ManagementProcedure[] {
    if (!manual) return [];

    // Select procedures based on alert type and troubleshooting guide
    const procedures: ManagementProcedure[] = [];

    if (alert.alert_type === 'node_outage') {
      procedures.push(...manual.management_procedures.filter((p: ManagementProcedure) =>
        p.category === 'troubleshooting' || p.name.includes('Reboot')
      ));
    } else if (alert.alert_type === 'degraded_service') {
      procedures.push(...manual.management_procedures.filter((p: ManagementProcedure) =>
        p.category === 'configuration' || p.category === 'monitoring'
      ));
    } else if (alert.alert_type === 'equipment_failure') {
      procedures.push(...manual.management_procedures.filter((p: ManagementProcedure) =>
        p.category === 'troubleshooting' || p.category === 'maintenance'
      ));
    }

    return procedures.slice(0, 3); // Limit to top 3 relevant procedures
  }

  private formatKPIsForTicket(kpis: KPIMetrics[]): string[] {
    if (kpis.length === 0) return ['No recent KPIs available'];

    const latest = kpis[kpis.length - 1];
    return [
      `DS SNR: ${latest.ds_snr_db.toFixed(1)} dB`,
      `Packet Loss: ${latest.packet_loss_percent.toFixed(2)}%`,
      `US SNR: ${latest.us_snr_db.toFixed(1)} dB`,
      `Latency: ${latest.latency_ms.toFixed(1)} ms`,
      `Downstream Throughput: ${latest.downstream_throughput_mbps.toFixed(1)} Mbps`,
      `Active Modems: ${latest.active_modems}`,
      `CPU Utilization: ${latest.node_cpu_utilization.toFixed(1)}%`,
      `Temperature: ${latest.node_temperature.toFixed(1)}°C`,
    ];
  }

  private identifyEnvironmentalFactors(node: FiberNode, alert: Alert): string[] {
    const factors = [];
    factors.push(`Region: ${node.region}`);
    factors.push(`Node Type: ${node.node_type || 'N/A'}`);
    if (alert.alert_type === 'equipment_failure') {
      factors.push('Check for water ingress, overheating, or physical damage');
    }
    if (node.power_supply_status && node.power_supply_status !== 'all_ok') {
      factors.push(`Power supply issue (${node.power_supply_status}) - check status`);
    }
    return factors;
  }

  private generateWorkInstructions(
    _node: FiberNode,
    alert: Alert,
    troubleshootingGuide?: TroubleshootingGuide,
    manual?: any,
    aiAnalysis?: any
  ): FieldServiceTicket['work_instructions'] {
    return {
      estimated_time: troubleshootingGuide?.estimated_resolution_time || aiAnalysis?.estimatedResolutionTime || '1-4 hours',
      required_skills: ['RF Technician', 'Network Engineer', troubleshootingGuide?.requires_vendor_support ? 'Vendor Certified' : ''].filter(Boolean),
      required_tools: troubleshootingGuide?.diagnostic_steps
        ? ['Multimeter', 'Spectrum Analyzer', 'Laptop with configuration tools', 'Safety equipment']
        : ['Standard toolkit', 'Laptop with console cable', 'Test UE'],
      safety_warnings: manual?.safety.warnings || [
        'RF RADIATION HAZARD: Maintain safe distance from active antennas',
        'HIGH VOLTAGE: Follow lockout/tagout procedures',
        'FALL HAZARD: Use proper fall protection at heights',
      ],
      step_by_step_procedure: this.buildProcedure(alert, troubleshootingGuide, aiAnalysis),
      verification_steps: [
        'Verify node status is HEALTHY in EMS',
        'Check all KPIs return to normal thresholds',
        'Test UE attachment and data session',
        'Confirm no critical alarms',
        'Update ticket with resolution notes',
      ],
      rollback_procedure: troubleshootingGuide?.diagnostic_steps.length ?
        ['Document current state', 'Restore previous configuration if available', 'Contact NOC for remote assistance'] :
        undefined,
    };
  }

  private buildProcedure(alert: Alert, troubleshootingGuide?: TroubleshootingGuide, aiAnalysis?: any): string[] {
    if (troubleshootingGuide) {
      return [
        ...troubleshootingGuide.diagnostic_steps.map(s => `[DIAGNOSTIC] ${s}`),
        ...troubleshootingGuide.resolution_steps.map(s => `[RESOLUTION] ${s}`),
      ];
    }

    if (aiAnalysis?.recommendations) {
      return aiAnalysis.recommendations.map((r: string) => `[AI RECOMMENDATION] ${r}`);
    }

    // Generic procedure based on alert type
    const procedures: Record<string, string[]> = {
      node_outage: [
        'Check power supply and battery backup',
        'Verify backhaul connectivity',
        'Check for alarms in EMS',
        'Perform soft reboot if no hardware issues found',
        'Escalate to vendor if problem persists',
      ],
      degraded_service: [
        'Check RF interference levels',
        'Verify antenna alignment',
        'Check backhaul utilization',
        'Review recent configuration changes',
        'Optimize RF parameters if needed',
      ],
      equipment_failure: [
        'Visual inspection of equipment',
        'Check for overheating or physical damage',
        'Review equipment logs',
        'Replace faulty component if identified',
        'Contact vendor for RMA if needed',
      ],
    };

    return procedures[alert.alert_type] || [
      'Perform site inspection',
      'Review diagnostic data',
      'Follow troubleshooting guide',
      'Document findings',
      'Implement fix or escalate',
    ];
  }
}

// Export singleton instance
export const ticketGenerationService = new TicketGenerationService();
