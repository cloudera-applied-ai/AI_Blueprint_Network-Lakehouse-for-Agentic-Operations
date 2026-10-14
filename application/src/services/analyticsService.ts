/**
 * Analytics service for identifying common issues from real network data
 */

import { Alert, SelfHealingAction, FiberNode, AlertType, IssueCategory } from '@/types';

export interface CommonIssueData {
  category: IssueCategory;
  description: string;
  occurrences: number;
  affectedNodes: number;
  trend: 'increasing' | 'stable' | 'decreasing';
  commonFactors: string[];
  affectedCities: string[];
}

/**
 * Analyzes alerts and actions to identify common issues with geographic patterns
 */
export const analyzeCommonIssues = (
  alerts: Alert[],
  _actions: SelfHealingAction[], // Reserved for future action pattern analysis
  nodes: FiberNode[]
): CommonIssueData[] => {
  // Create node lookup for fast access
  const nodeMap = new Map(nodes.map(t => [t.node_id, t]));

  // Group alerts by type
  const alertsByType = new Map<AlertType, Alert[]>();
  alerts.forEach(alert => {
    const existing = alertsByType.get(alert.alert_type) || [];
    alertsByType.set(alert.alert_type, [...existing, alert]);
  });

  const issues: CommonIssueData[] = [];

  // Analyze each alert type
  alertsByType.forEach((typeAlerts, alertType) => {
    if (typeAlerts.length < 3) return; // Skip if too few occurrences

    // Get affected nodes and cities
    const affectedNodeIds = new Set(typeAlerts.map(a => a.node_id));
    const affectedCities = new Set<string>();
    const cityOccurrences = new Map<string, number>();

    affectedNodeIds.forEach(nodeId => {
      const node = nodeMap.get(nodeId);
      if (node?.city) {
        affectedCities.add(node.city);
        cityOccurrences.set(node.city, (cityOccurrences.get(node.city) || 0) + 1);
      }
    });

    // Get top 3 affected cities
    const topCities = Array.from(cityOccurrences.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([city]) => city);

    // Determine trend (simple: check if recent alerts are increasing)
    const recentThreshold = new Date(Date.now() - 30 * 60 * 1000); // Last 30 minutes
    const recentCount = typeAlerts.filter(a => a.timestamp >= recentThreshold).length;
    const trend = recentCount > typeAlerts.length * 0.4 ? 'increasing' : 'stable';

    // Map alert type to issue
    const issue = createIssueFromAlertType(
      alertType,
      typeAlerts.length,
      affectedNodeIds.size,
      trend,
      topCities
    );

    if (issue) {
      issues.push(issue);
    }
  });

  // Sort by occurrences (most common first)
  return issues.sort((a, b) => b.occurrences - a.occurrences).slice(0, 5);
};

/**
 * Maps alert type to a common issue with appropriate category and factors
 */
const createIssueFromAlertType = (
  alertType: AlertType,
  occurrences: number,
  affectedNodes: number,
  trend: 'increasing' | 'stable' | 'decreasing',
  affectedCities: string[]
): CommonIssueData | null => {
  const cityList = affectedCities.length > 0
    ? affectedCities.join(', ')
    : 'Multiple locations';

  switch (alertType) {
    case AlertType.NODE_OUTAGE:
      return {
        category: IssueCategory.EQUIPMENT,
        description: 'Fiber node outages',
        occurrences,
        affectedNodes,
        trend,
        commonFactors: ['Equipment failure', 'Power supply issues'],
        affectedCities: [cityList]
      };

    case AlertType.DEGRADED_SERVICE:
      return {
        category: IssueCategory.CONFIGURATION,
        description: 'Service degradation',
        occurrences,
        affectedNodes,
        trend,
        commonFactors: ['Configuration drift', 'Suboptimal parameters'],
        affectedCities: [cityList]
      };

    case AlertType.HIGH_PACKET_LOSS:
      return {
        category: IssueCategory.CONFIGURATION,
        description: 'High packet loss rate',
        occurrences,
        affectedNodes,
        trend,
        commonFactors: ['RF interference', 'Signal degradation'],
        affectedCities: [cityList]
      };

    case AlertType.CONGESTION:
      return {
        category: IssueCategory.CAPACITY,
        description: 'Network congestion',
        occurrences,
        affectedNodes,
        trend,
        commonFactors: ['Peak hour traffic', 'Insufficient capacity'],
        affectedCities: [cityList]
      };

    case AlertType.EQUIPMENT_FAILURE:
      return {
        category: IssueCategory.EQUIPMENT,
        description: 'Equipment hardware failures',
        occurrences,
        affectedNodes,
        trend,
        commonFactors: ['Component aging', 'Environmental stress'],
        affectedCities: [cityList]
      };

    case AlertType.SIGNAL_DEGRADATION:
      return {
        category: IssueCategory.CONFIGURATION,
        description: 'Signal degradation',
        occurrences,
        affectedNodes,
        trend,
        commonFactors: ['Poor SNR levels', 'Ingress noise'],
        affectedCities: [cityList]
      };

    default:
      return null;
  }
};
