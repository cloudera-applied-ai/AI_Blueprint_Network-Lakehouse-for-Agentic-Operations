/**
 * Crew Dispatch Service - Manages field crew dispatches for hardware interventions
 */

import { CrewDispatch } from '@/types/llm';
import { FiberNode, Alert } from '@/types';

class CrewDispatchService {
  private dispatches: Map<string, CrewDispatch> = new Map();
  private crewTeams: string[] = [
    'Alpha Team', 'Bravo Team', 'Charlie Team', 'Delta Team',
    'Echo Team', 'Foxtrot Team', 'Golf Team', 'Hotel Team'
  ];

  /**
   * Create a crew dispatch for hardware issues
   */
  createDispatch(
    node: FiberNode,
    alert: Alert,
    issueType: CrewDispatch['issueType'],
    description: string,
    aiInitiated: boolean = true,
    relatedPlanId?: string
  ): CrewDispatch {
    const dispatch: CrewDispatch = {
      id: `crew-${Date.now()}-${Math.random().toString(36).substring(7)}`,
      timestamp: new Date(),
      nodeId: node.node_id,
      issueType,
      severity: this.mapAlertSeverityToCrewSeverity(alert.severity),
      description,
      location: {
        city: node.city || '',
        region: node.region,
        coordinates: {
          lat: node.latitude,
          lng: node.longitude,
        },
      },
      assignedCrew: this.assignCrew(),
      estimatedArrival: this.calculateETA(),
      status: 'dispatched',
      dispatchTime: new Date(),
      aiInitiated,
      relatedPlanId,
    };

    this.dispatches.set(dispatch.id, dispatch);
    console.log(`🚁 Crew Dispatched: ${dispatch.assignedCrew} to ${node.city} for ${issueType}`);

    return dispatch;
  }

  /**
   * Process crew dispatches - simulate crew progress
   */
  processDispatches(): void {
    const now = new Date();

    this.dispatches.forEach((dispatch) => {
      const timeElapsed = now.getTime() - dispatch.dispatchTime.getTime();

      switch (dispatch.status) {
        case 'dispatched':
          // Crew departs immediately
          if (timeElapsed > 5000) { // 5 seconds
            dispatch.status = 'en_route';
            console.log(`🚗 ${dispatch.assignedCrew} en route to ${dispatch.location.city}`);
          }
          break;

        case 'en_route':
          // Crew arrives based on ETA (15-45 seconds)
          if (dispatch.estimatedArrival && now >= dispatch.estimatedArrival) {
            dispatch.status = 'on_site';
            dispatch.arrivalTime = now;
            console.log(`📍 ${dispatch.assignedCrew} arrived at ${dispatch.location.city}`);
          }
          break;

        case 'on_site':
          // Work takes 20-60 seconds depending on severity
          const workDuration = this.getWorkDuration(dispatch.severity);
          const onSiteTime = dispatch.arrivalTime
            ? now.getTime() - dispatch.arrivalTime.getTime()
            : 0;

          if (onSiteTime > workDuration) {
            dispatch.status = 'completed';
            dispatch.completionTime = now;
            dispatch.workLog = this.generateWorkLog(dispatch);
            console.log(`✅ ${dispatch.assignedCrew} completed work at ${dispatch.location.city}`);
          }
          break;
      }
    });
  }

  /**
   * Get all dispatches
   */
  getAllDispatches(): CrewDispatch[] {
    return Array.from(this.dispatches.values())
      .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
  }

  /**
   * Get active dispatches
   */
  getActiveDispatches(): CrewDispatch[] {
    return this.getAllDispatches().filter(
      (d) => d.status !== 'completed' && d.status !== 'cancelled'
    );
  }

  /**
   * Get dispatches for a specific node
   */
  getDispatchesForNode(nodeId: string): CrewDispatch[] {
    return this.getAllDispatches().filter((d) => d.nodeId === nodeId);
  }

  /**
   * Assign a crew team (round-robin)
   */
  private assignCrew(): string {
    const availableCrews = this.crewTeams.filter((team) => {
      const activeDispatches = Array.from(this.dispatches.values()).filter(
        (d) => d.assignedCrew === team && d.status !== 'completed' && d.status !== 'cancelled'
      );
      return activeDispatches.length === 0; // Crew is available
    });

    if (availableCrews.length > 0) {
      return availableCrews[0];
    }

    // All crews busy, assign least busy
    return this.crewTeams[Math.floor(Math.random() * this.crewTeams.length)];
  }

  /**
   * Calculate estimated time of arrival (15-45 seconds from now)
   */
  private calculateETA(): Date {
    const etaMs = 15000 + Math.random() * 30000; // 15-45 seconds
    return new Date(Date.now() + etaMs);
  }

  /**
   * Get work duration based on severity
   */
  private getWorkDuration(severity: CrewDispatch['severity']): number {
    switch (severity) {
      case 'critical':
        return 20000; // 20 seconds
      case 'high':
        return 30000; // 30 seconds
      case 'medium':
        return 45000; // 45 seconds
      case 'low':
        return 60000; // 60 seconds
      default:
        return 30000;
    }
  }

  /**
   * Map alert severity to crew severity
   */
  private mapAlertSeverityToCrewSeverity(alertSeverity: string): CrewDispatch['severity'] {
    switch (alertSeverity) {
      case 'critical':
        return 'critical';
      case 'warning':
        return 'high';
      case 'info':
        return 'medium';
      default:
        return 'medium';
    }
  }

  /**
   * Generate work log after completion
   */
  private generateWorkLog(dispatch: CrewDispatch): string {
    const logs = {
      hardware_failure: [
        'Replaced faulty power amplifier module',
        'Replaced damaged antenna connector',
        'Replaced malfunctioning baseband unit',
        'Repaired power supply unit',
      ],
      antenna_alignment: [
        'Adjusted antenna azimuth and tilt',
        'Realigned antenna to optimize coverage',
        'Corrected antenna positioning after wind damage',
      ],
      power_system: [
        'Replaced backup battery',
        'Fixed power distribution issue',
        'Repaired solar panel connection',
      ],
      connectivity: [
        'Replaced fiber optic cable',
        'Fixed microwave link alignment',
        'Repaired backhaul connection',
      ],
      preventive_maintenance: [
        'Completed routine inspection',
        'Cleaned and lubricated antenna mechanisms',
        'Verified all systems operational',
      ],
    };

    const options = logs[dispatch.issueType] || ['Completed maintenance work'];
    const action = options[Math.floor(Math.random() * options.length)];

    return `${action}. Node returned to service. All KPIs within normal range.`;
  }

  /**
   * Clear old completed dispatches (keep last 50)
   */
  cleanup(): void {
    const all = this.getAllDispatches();
    const completed = all.filter((d) => d.status === 'completed');

    if (completed.length > 50) {
      const toRemove = completed.slice(50);
      toRemove.forEach((d) => this.dispatches.delete(d.id));
    }
  }
}

// Singleton instance
export const crewDispatchService = new CrewDispatchService();
