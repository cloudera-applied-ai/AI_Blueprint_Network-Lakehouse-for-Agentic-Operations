/**
 * Hardware Manual Service
 * Generates comprehensive support documentation for all node equipment
 * Used by AI agents for troubleshooting and ticket dispatch
 */

import { MANUFACTURERS, HARDWARE_MODELS } from '@/constants';

export interface HardwareManual {
  manufacturer: string;
  model: string;
  manual_id: string;

  // Specifications
  specifications: {
    model_number: string;
    form_factor: string;
    dimensions: string;
    weight: string;
    power_requirements: string;
    supported_technologies: string[];
    frequency_bands: string[];
    max_tx_power: string;
    cooling: string;
  };

  // Operating Limits
  operating_limits: {
    temperature_range: string;
    humidity_range: string;
    altitude_max: string;
    power_input_range: string;
    vswr_max: string;
    vibration_tolerance: string;
  };

  // Management Procedures
  management_procedures: ManagementProcedure[];

  // Common Issues & Troubleshooting
  troubleshooting: TroubleshootingGuide[];

  // Maintenance Schedule
  maintenance_schedule: {
    daily: string[];
    weekly: string[];
    monthly: string[];
    quarterly: string[];
    annual: string[];
  };

  // Safety & Compliance
  safety: {
    warnings: string[];
    rf_exposure_limits: string;
    electrical_safety: string;
    certifications: string[];
  };

  // Support Contact
  support_contact: {
    phone: string;
    email: string;
    portal: string;
    escalation_procedure: string;
  };
}

export interface ManagementProcedure {
  procedure_id: string;
  name: string;
  category: 'configuration' | 'monitoring' | 'maintenance' | 'upgrade' | 'troubleshooting';
  estimated_time: string;
  required_access_level: string;
  required_tools: string[];
  steps: string[];
  verification_steps: string[];
  rollback_procedure?: string[];
}

export interface TroubleshootingGuide {
  issue_id: string;
  symptom: string;
  severity: 'critical' | 'major' | 'minor';
  possible_causes: string[];
  diagnostic_steps: string[];
  resolution_steps: string[];
  estimated_resolution_time: string;
  requires_site_visit: boolean;
  requires_vendor_support: boolean;
  related_manual_sections: string[];
  preventive_measures: string[];
}

class HardwareManualService {
  private manuals: Map<string, HardwareManual> = new Map();

  constructor() {
    this.generateAllManuals();
  }

  /**
   * Generate manuals for all manufacturer/model combinations
   */
  private generateAllManuals(): void {
    MANUFACTURERS.forEach(manufacturer => {
      const models = HARDWARE_MODELS[manufacturer];
      models.forEach(model => {
        const manual = this.generateManual(manufacturer, model);
        const key = `${manufacturer}-${model}`;
        this.manuals.set(key, manual);
      });
    });

    console.log(`✅ Generated ${this.manuals.size} hardware support manuals`);
  }

  /**
   * Get manual for specific hardware
   */
  getManual(manufacturer: string, model: string): HardwareManual | null {
    const key = `${manufacturer}-${model}`;
    return this.manuals.get(key) || null;
  }

  /**
   * Get troubleshooting guide for specific issue
   */
  getTroubleshootingGuide(
    manufacturer: string,
    model: string,
    symptom: string
  ): TroubleshootingGuide | null {
    const manual = this.getManual(manufacturer, model);
    if (!manual) return null;

    // Find best matching troubleshooting guide
    const guide = manual.troubleshooting.find(g =>
      g.symptom.toLowerCase().includes(symptom.toLowerCase()) ||
      symptom.toLowerCase().includes(g.symptom.toLowerCase())
    );

    return guide || manual.troubleshooting[0]; // Return first guide as fallback
  }

  /**
   * Get all manuals (for search/reference)
   */
  getAllManuals(): HardwareManual[] {
    return Array.from(this.manuals.values());
  }

  /**
   * Search manuals by keyword
   */
  searchManuals(keyword: string): HardwareManual[] {
    const lowerKeyword = keyword.toLowerCase();
    return this.getAllManuals().filter(manual =>
      manual.manufacturer.toLowerCase().includes(lowerKeyword) ||
      manual.model.toLowerCase().includes(lowerKeyword) ||
      manual.troubleshooting.some(t =>
        t.symptom.toLowerCase().includes(lowerKeyword) ||
        t.possible_causes.some(c => c.toLowerCase().includes(lowerKeyword))
      )
    );
  }

  /**
   * Generate comprehensive manual for a specific model
   */
  private generateManual(manufacturer: string, model: string): HardwareManual {
    const manual_id = `MAN-${manufacturer.substring(0, 3).toUpperCase()}-${model.replace(/\s/g, '-')}`;

    return {
      manufacturer,
      model,
      manual_id,
      specifications: this.generateSpecifications(manufacturer, model),
      operating_limits: this.generateOperatingLimits(manufacturer, model),
      management_procedures: this.generateManagementProcedures(manufacturer, model),
      troubleshooting: this.generateTroubleshootingGuides(manufacturer, model),
      maintenance_schedule: this.generateMaintenanceSchedule(manufacturer, model),
      safety: this.generateSafetyInfo(manufacturer, model),
      support_contact: this.generateSupportContact(manufacturer),
    };
  }

  private generateSpecifications(_manufacturer: string, model: string): HardwareManual['specifications'] {
    const isBaseband = model.includes('BB') || model.includes('Baseband');
    const is5G = model.includes('5G') || model.includes('AIR') || model.includes('AAU');

    return {
      model_number: `${model}-${Math.floor(Math.random() * 1000)}`,
      form_factor: isBaseband ? '19" Rack Mount (3U)' : 'Outdoor Remote Radio Head',
      dimensions: isBaseband ? '482 x 133 x 450 mm' : '700 x 330 x 180 mm',
      weight: isBaseband ? '15-25 kg' : '18-35 kg',
      power_requirements: isBaseband ? '220V AC, 1500W max' : '48V DC, 500-1200W',
      supported_technologies: is5G ? ['5G NR', '4G LTE', '3G UMTS'] : ['4G LTE', '3G UMTS', '2G GSM'],
      frequency_bands: is5G
        ? ['700 MHz', '1800 MHz', '2600 MHz', '3500 MHz', '28 GHz']
        : ['700 MHz', '1800 MHz', '2100 MHz', '2600 MHz'],
      max_tx_power: is5G ? '200W (53 dBm)' : '80W (49 dBm)',
      cooling: isBaseband ? 'Active cooling with redundant fans' : 'Passive cooling with heat sink',
    };
  }

  private generateOperatingLimits(_manufacturer: string, _model: string): HardwareManual['operating_limits'] {
    return {
      temperature_range: '-40°C to +55°C (outdoor), +5°C to +40°C (indoor)',
      humidity_range: '5% to 95% RH (non-condensing)',
      altitude_max: '4000 meters above sea level',
      power_input_range: '36V to 60V DC (nominal 48V)',
      vswr_max: '1.5:1 (return loss > 14 dB)',
      vibration_tolerance: 'IEC 60068-2-64 compliant',
    };
  }

  private generateManagementProcedures(_manufacturer: string, _model: string): ManagementProcedure[] {
    return [
      {
        procedure_id: 'PROC-001',
        name: 'Initial Configuration',
        category: 'configuration',
        estimated_time: '45-60 minutes',
        required_access_level: 'Engineer',
        required_tools: ['Console cable', 'Configuration laptop', 'Network analyzer'],
        steps: [
          'Connect to management port via console cable (115200 baud, 8N1)',
          'Login with default credentials (change immediately)',
          'Configure management IP address and gateway',
          'Set system hostname and location',
          'Configure NTP servers for time synchronization',
          'Upload site-specific configuration file',
          'Configure RF parameters (frequency, power, bandwidth)',
          'Set up alarm and SNMP monitoring',
          'Configure redundancy and failover settings',
          'Verify backhaul connectivity',
        ],
        verification_steps: [
          'Ping management interface from NOC',
          'Verify NTP synchronization status',
          'Check alarm reporting to EMS',
          'Verify RF output power with spectrum analyzer',
          'Confirm cell is visible to test UE',
        ],
        rollback_procedure: [
          'Restore previous configuration from backup',
          'Reboot unit to apply saved configuration',
          'Verify connectivity and services',
        ],
      },
      {
        procedure_id: 'PROC-002',
        name: 'Software Upgrade',
        category: 'upgrade',
        estimated_time: '30-45 minutes',
        required_access_level: 'Senior Engineer',
        required_tools: ['FTP/SFTP server', 'Configuration backup', 'Rollback plan'],
        steps: [
          'Review release notes and compatibility matrix',
          'Backup current configuration and license files',
          'Schedule maintenance window (2-4 AM recommended)',
          'Upload new software image to device',
          'Verify MD5 checksum of uploaded image',
          'Set boot parameters to new software version',
          'Initiate controlled reboot',
          'Monitor boot process and alarm status',
          'Verify software version after reboot',
          'Run post-upgrade health checks',
          'Restore configuration if needed',
          'Update EMS/NMS with new version',
        ],
        verification_steps: [
          'Check software version: show system version',
          'Verify all services are operational',
          'Check for critical alarms',
          'Test UE attachment and data session',
          'Verify KPI metrics within normal range',
        ],
        rollback_procedure: [
          'Set boot parameters to previous software version',
          'Reboot device',
          'Verify services after rollback',
          'Restore previous configuration if needed',
        ],
      },
      {
        procedure_id: 'PROC-003',
        name: 'Cell Reboot (Soft Reset)',
        category: 'troubleshooting',
        estimated_time: '5-10 minutes',
        required_access_level: 'Engineer',
        required_tools: ['CLI access or EMS'],
        steps: [
          'Verify no active maintenance or upgrades',
          'Check current active users (minimize impact)',
          'Issue soft reboot command: "reset system soft"',
          'Monitor reboot progress via console or syslog',
          'Wait for system to complete initialization (3-5 min)',
          'Verify all interfaces are up',
          'Check alarm status',
        ],
        verification_steps: [
          'Verify uptime has reset: show system uptime',
          'Check all services: show service status',
          'Verify cell is broadcasting: check with test UE',
          'Confirm no critical alarms',
        ],
      },
      {
        procedure_id: 'PROC-004',
        name: 'Antenna Alignment Adjustment',
        category: 'maintenance',
        estimated_time: '60-90 minutes',
        required_access_level: 'Field Technician',
        required_tools: ['Torque wrench', 'Inclinometer', 'Compass', 'Spectrum analyzer', 'Safety harness'],
        steps: [
          'Review target azimuth and tilt from RF plan',
          'Access site safely (fall protection required)',
          'Measure current antenna orientation',
          'Document current settings (photo evidence)',
          'Loosen antenna mounting brackets',
          'Adjust azimuth using compass (magnetic declination corrected)',
          'Adjust mechanical tilt using inclinometer',
          'Adjust electrical tilt via RET control',
          'Tighten brackets to specified torque (45 Nm)',
          'Verify with RF measurements',
          'Update site documentation',
        ],
        verification_steps: [
          'Measure RSRP in planned coverage area',
          'Check for interference to adjacent cells',
          'Verify coverage matches RF plan',
          'Document final azimuth and tilt',
        ],
      },
      {
        procedure_id: 'PROC-005',
        name: 'Performance Monitoring Setup',
        category: 'monitoring',
        estimated_time: '20-30 minutes',
        required_access_level: 'Engineer',
        required_tools: ['EMS access', 'SNMP manager'],
        steps: [
          'Configure performance counters collection',
          'Set KPI thresholds (RRC success, ERAB success, latency)',
          'Enable SNMP traps for critical alarms',
          'Configure syslog forwarding to central server',
          'Set up automated reports (daily/weekly)',
          'Test alarm notification path',
        ],
        verification_steps: [
          'Verify counters are incrementing',
          'Test alarm generation and notification',
          'Check data appears in monitoring dashboard',
        ],
      },
    ];
  }

  private generateTroubleshootingGuides(_manufacturer: string, _model: string): TroubleshootingGuide[] {
    return [
      {
        issue_id: 'ISSUE-001',
        symptom: 'Cell Outage - No Service',
        severity: 'critical',
        possible_causes: [
          'Power supply failure',
          'Backhaul connectivity loss',
          'Software crash or hang',
          'RF unit failure',
          'License expiration',
          'Configuration error after change',
        ],
        diagnostic_steps: [
          'Check power LEDs on unit',
          'Verify power input voltage (36-60V DC)',
          'Check backhaul link status (fiber/microwave)',
          'Ping management IP from NOC',
          'Check EMS for alarms',
          'Review recent configuration changes',
          'Check license validity: show license status',
          'Verify RF output power with spectrum analyzer',
        ],
        resolution_steps: [
          'If power issue: Check circuit breakers, rectifiers, battery backup',
          'If backhaul issue: Check fiber/cable connections, check switch ports',
          'If software crash: Perform soft reboot (PROC-003)',
          'If RF failure: Check coax cables, measure VSWR, check for water ingress',
          'If license expired: Upload new license file',
          'If config error: Restore previous working configuration',
          'If persistent: Escalate to vendor support',
        ],
        estimated_resolution_time: '15-60 minutes',
        requires_site_visit: true,
        requires_vendor_support: false,
        related_manual_sections: ['PROC-003', 'Power System Maintenance'],
        preventive_measures: [
          'Regular battery backup testing',
          'Proactive license renewal',
          'Configuration change management process',
          'Redundant backhaul where critical',
        ],
      },
      {
        issue_id: 'ISSUE-002',
        symptom: 'High Call Drop Rate',
        severity: 'major',
        possible_causes: [
          'RF interference',
          'Antenna misalignment or damage',
          'Neighbor cell list errors',
          'Insufficient coverage overlap',
          'Hardware degradation (PA failure)',
          'Backhaul congestion',
        ],
        diagnostic_steps: [
          'Check call drop KPI trend (sudden vs gradual)',
          'Review RF interference alarms',
          'Check antenna VSWR and return loss',
          'Verify neighbor cell configuration',
          'Drive test affected area',
          'Check backhaul utilization',
          'Review power amplifier status',
        ],
        resolution_steps: [
          'If interference: Use spectrum analyzer to identify source, coordinate with adjacent operators',
          'If antenna issue: Perform alignment check (PROC-004), replace if damaged',
          'If channel map error: Update channel frequency plan, optimize RF parameters',
          'If coverage gap: Adjust antenna tilt, increase power (within limits), add neighbor cell',
          'If PA degradation: Replace power amplifier module',
          'If backhaul congestion: Upgrade backhaul capacity or enable compression',
        ],
        estimated_resolution_time: '2-24 hours',
        requires_site_visit: true,
        requires_vendor_support: false,
        related_manual_sections: ['PROC-004', 'RF Optimization'],
        preventive_measures: [
          'Regular antenna inspection and alignment',
          'Neighbor cell optimization',
          'Continuous RF monitoring',
          'Preventive hardware replacement',
        ],
      },
      {
        issue_id: 'ISSUE-003',
        symptom: 'High Temperature Alarm',
        severity: 'major',
        possible_causes: [
          'Fan failure',
          'Air filter blockage',
          'Ambient temperature too high',
          'Cabinet door left open',
          'Cooling system malfunction',
          'Excessive RF power output',
        ],
        diagnostic_steps: [
          'Check temperature readings: show environment temperature',
          'Check fan status: show environment fans',
          'Inspect air filters for dust/blockage',
          'Check cabinet doors are closed and sealed',
          'Verify ambient temperature',
          'Check for direct sunlight exposure',
          'Review power consumption and RF output',
        ],
        resolution_steps: [
          'If fan failure: Replace failed fan immediately',
          'If filter blockage: Clean or replace air filters',
          'If ambient too high: Add supplemental cooling, improve ventilation',
          'If door open: Close and secure cabinet',
          'If sunlight: Install sunshield or relocate equipment',
          'If excessive power: Reduce RF output power temporarily',
          'If persistent: Install additional cooling fans',
        ],
        estimated_resolution_time: '30 minutes - 2 hours',
        requires_site_visit: true,
        requires_vendor_support: false,
        related_manual_sections: ['Cooling System Maintenance', 'Environmental Limits'],
        preventive_measures: [
          'Monthly air filter cleaning',
          'Quarterly fan inspection',
          'Temperature monitoring and trending',
          'Proper cabinet ventilation design',
        ],
      },
      {
        issue_id: 'ISSUE-004',
        symptom: 'Degraded Service - Low Throughput',
        severity: 'major',
        possible_causes: [
          'Backhaul congestion or errors',
          'RF interference',
          'Excessive user load',
          'Scheduler misconfiguration',
          'Antenna feeder damage',
          'Software bug',
        ],
        diagnostic_steps: [
          'Check backhaul utilization and error rates',
          'Review throughput KPIs by time of day',
          'Check active user count and PRB utilization',
          'Analyze interference levels',
          'Check MIMO/beamforming status',
          'Review recent software/config changes',
        ],
        resolution_steps: [
          'If backhaul issue: Upgrade link capacity, check for errors/packet loss',
          'If interference: Identify source, adjust frequency if possible',
          'If congestion: Enable carrier aggregation, add capacity',
          'If misconfiguration: Optimize scheduler parameters',
          'If feeder damage: Test cables with TDR, replace if faulty',
          'If software bug: Apply vendor patch or rollback',
        ],
        estimated_resolution_time: '1-8 hours',
        requires_site_visit: false,
        requires_vendor_support: false,
        related_manual_sections: ['Backhaul Optimization', 'RF Tuning'],
        preventive_measures: [
          'Capacity monitoring and planning',
          'Regular cable and connector inspection',
          'Software stability testing before deployment',
        ],
      },
      {
        issue_id: 'ISSUE-005',
        symptom: 'Signal Degradation',
        severity: 'major',
        possible_causes: [
          'Channel frequency plan errors',
          'Timing/synchronization issues',
          'RF coverage gaps',
          'Parameter mismatch between nodes',
          'Trunk interface errors',
          'RF parameter tuning needed',
        ],
        diagnostic_steps: [
          'Check upstream SNR per service group',
          'Verify channel frequency plan is correct',
          'Check node synchronization status',
          'Verify trunk interface connectivity',
          'Review RF parameters (power levels, tilt)',
          'Sweep test node service area',
        ],
        resolution_steps: [
          'If frequency plan error: Update channel assignments',
          'If timing issue: Check clock source, verify synchronization',
          'If coverage gap: Adjust RF levels, add amplifiers',
          'If parameter mismatch: Align RF parameters across nodes',
          'If trunk error: Check fiber connectivity, restart interfaces',
          'If tuning needed: Optimize power levels, equalizer settings',
        ],
        estimated_resolution_time: '1-4 hours',
        requires_site_visit: false,
        requires_vendor_support: false,
        related_manual_sections: ['Mobility Optimization', 'Synchronization'],
        preventive_measures: [
          'Automated neighbor cell discovery',
          'Regular synchronization monitoring',
          'Mobility parameter optimization',
        ],
      },
      {
        issue_id: 'ISSUE-006',
        symptom: 'Equipment Not Responding',
        severity: 'critical',
        possible_causes: [
          'Software crash',
          'Power loss or failure',
          'Network connectivity loss',
          'Hardware failure (CPU/memory)',
          'Configuration corruption',
        ],
        diagnostic_steps: [
          'Check if unit has power (LEDs, fans)',
          'Check network connectivity (ping, trace)',
          'Try accessing via out-of-band management',
          'Check EMS last contact time',
          'Verify no recent upgrades or changes',
        ],
        resolution_steps: [
          'If power issue: Check power source, cables, breakers',
          'If network issue: Check cables, switch ports, routing',
          'If software crash: Power cycle unit (last resort)',
          'If hardware failure: Replace faulty module/unit',
          'If config corruption: Restore from backup',
          'If persistent: Contact vendor support with serial number',
        ],
        estimated_resolution_time: '15 minutes - 4 hours',
        requires_site_visit: true,
        requires_vendor_support: true,
        related_manual_sections: ['Recovery Procedures', 'RMA Process'],
        preventive_measures: [
          'Regular configuration backups',
          'Proactive hardware health monitoring',
          'Software stability validation',
        ],
      },
    ];
  }

  private generateMaintenanceSchedule(_manufacturer: string, _model: string): HardwareManual['maintenance_schedule'] {
    return {
      daily: [
        'Check alarm dashboard for new critical alerts',
        'Verify site is accessible remotely',
      ],
      weekly: [
        'Review KPI trends and thresholds',
        'Check backup power system status',
        'Verify software/firmware versions are current',
      ],
      monthly: [
        'Clean air filters',
        'Inspect physical connections and cables',
        'Review and clear old alarm history',
        'Backup configuration files',
        'Check disk space and log rotation',
      ],
      quarterly: [
        'Physical site inspection',
        'Antenna alignment verification',
        'Battery backup load test',
        'Software patch review and planning',
        'Grounding and lightning protection inspection',
      ],
      annual: [
        'Comprehensive RF optimization',
        'Replace air filters',
        'Cooling system deep clean',
        'Calibration verification',
        'Lightning protection system testing',
        'Power system preventive maintenance',
        'Review and update emergency procedures',
      ],
    };
  }

  private generateSafetyInfo(_manufacturer: string, _model: string): HardwareManual['safety'] {
    return {
      warnings: [
        'RF RADIATION HAZARD: Maintain minimum 2 meter distance from active antennas',
        'HIGH VOLTAGE: Only qualified personnel should access power systems',
        'FALL HAZARD: Use proper fall protection when working at height',
        'HEAVY EQUIPMENT: Use proper lifting techniques, equipment weighs 15-35 kg',
        'HOT SURFACES: Allow cooling period before touching heat sinks',
      ],
      rf_exposure_limits: 'FCC/ICNIRP compliant. Maintain exclusion zones per site license.',
      electrical_safety: 'Disconnect power before servicing. Use insulated tools. Follow lockout/tagout procedures.',
      certifications: [
        'CE Marking (European Conformity)',
        'FCC Part 15 (United States)',
        'IC RSS (Industry Canada)',
        'RoHS Compliant',
        'NEBS Level 3 Certified',
      ],
    };
  }

  private generateSupportContact(manufacturer: string): HardwareManual['support_contact'] {
    const supportMap: Record<string, HardwareManual['support_contact']> = {
      'Ericsson': {
        phone: '+1-888-374-2777',
        email: 'support@ericsson.com',
        portal: 'https://support.ericsson.com',
        escalation_procedure: 'P1 (Critical): Immediate phone call. P2 (Major): Within 1 hour. P3 (Minor): Within 4 hours.',
      },
      'Nokia': {
        phone: '+1-888-665-4228',
        email: 'customer.support@nokia.com',
        portal: 'https://nokia.com/support',
        escalation_procedure: 'Critical: Call TAC hotline. Major: Submit case online. Minor: Email support.',
      },
      'Huawei': {
        phone: '+86-755-2878-0808',
        email: 'support@huawei.com',
        portal: 'https://support.huawei.com',
        escalation_procedure: 'Severity 1: Immediate escalation to duty manager. Severity 2-4: Follow standard TAC process.',
      },
      'Samsung': {
        phone: '+82-2-2255-0114',
        email: 'network.support@samsung.com',
        portal: 'https://networks.samsung.com/support',
        escalation_procedure: 'Emergency: 24/7 hotline. Standard: Business hours support. Escalate to account manager if needed.',
      },
      'ZTE': {
        phone: '+86-755-2677-0000',
        email: 'support@zte.com.cn',
        portal: 'https://support.zte.com.cn',
        escalation_procedure: 'Critical: Phone escalation to regional TAC. Non-critical: Online ticketing system.',
      },
      'NEC': {
        phone: '+81-3-3798-6511',
        email: 'support@nec.com',
        portal: 'https://nec.com/support',
        escalation_procedure: 'Urgent: Contact account manager directly. Standard: Submit through support portal.',
      },
    };

    return supportMap[manufacturer] || supportMap['Ericsson'];
  }
}

// Export singleton instance
export const hardwareManualService = new HardwareManualService();
