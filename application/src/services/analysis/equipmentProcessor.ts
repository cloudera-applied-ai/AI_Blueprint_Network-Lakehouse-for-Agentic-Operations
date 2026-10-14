/**
 * Equipment Processor - Sensor data processing and formatting
 * Handles equipment data processing, sensor metric calculations, and report population
 */

import { FiberNode } from '@/types';
import {
  getAllSensorData,
  insertAntennaSensors,
  insertWeatherData,
  insertEnvSensors,
  insertEquipmentSensors,
} from '../memoryStore';
import { generateAllSensorData } from '../sensorDataGenerator';
import { NodeAnalysisReport, toDate } from './types';

/**
 * Populate equipment status from sensor data (called regardless of LLM availability)
 */
export function populateEquipmentFromSensors(
  report: NodeAnalysisReport,
  node: FiberNode
): void {
  // Equipment summary
  const daysSinceMaintenance = Math.floor(
    (Date.now() - toDate(node.last_maintenance).getTime()) / (1000 * 60 * 60 * 24)
  );

  // Get sensor data for this node - generate on-demand if not available
  let sensorData = getAllSensorData(node.node_id);

  // If no sensor data exists, generate it on-demand for this node
  if (!sensorData.equipment || !sensorData.antenna || !sensorData.environmental) {
    console.log(`Generating sensor data on-demand for node ${node.node_id}`);
    const generatedSensors = generateAllSensorData(node, new Date());

    // Insert the generated sensor data into the store
    if (generatedSensors.antenna) {
      insertAntennaSensors([generatedSensors.antenna]);
    }
    if (generatedSensors.weather) {
      insertWeatherData([generatedSensors.weather]);
    }
    if (generatedSensors.environmental) {
      insertEnvSensors([generatedSensors.environmental]);
    }
    if (generatedSensors.equipment) {
      insertEquipmentSensors([generatedSensors.equipment]);
    }

    // Re-fetch sensor data after generation
    sensorData = getAllSensorData(node.node_id);
  }

  const equipmentSensor = sensorData.equipment;
  const antennaSensor = sensorData.antenna;
  const envSensor = sensorData.environmental;

  report.equipmentStatus.summary = `${node.manufacturer} ${node.hardware_model} with firmware ${node.firmware_version}. ` +
    `Last maintenance was ${daysSinceMaintenance} days ago.`;

  // Detailed hardware health assessment from sensor data
  if (equipmentSensor && equipmentSensor.component_health.length > 0) {
    const healthyComponents = equipmentSensor.component_health.filter(c => c.status === 'healthy').length;
    const degradedComponents = equipmentSensor.component_health.filter(c => c.status === 'degraded').length;
    const criticalComponents = equipmentSensor.component_health.filter(c => c.status === 'critical' || c.status === 'failed').length;
    const totalComponents = equipmentSensor.component_health.length;
    const avgHealthScore = equipmentSensor.component_health.reduce((s, c) => s + c.health_score, 0) / totalComponents;

    // Build detailed hardware health string
    const healthDetails: string[] = [];
    if (criticalComponents > 0) {
      const criticalNames = equipmentSensor.component_health
        .filter(c => c.status === 'critical' || c.status === 'failed')
        .map(c => c.component_name)
        .join(', ');
      healthDetails.push(`${criticalComponents} CRITICAL component(s): ${criticalNames}`);
    }
    if (degradedComponents > 0) {
      const degradedNames = equipmentSensor.component_health
        .filter(c => c.status === 'degraded')
        .map(c => c.component_name)
        .join(', ');
      healthDetails.push(`${degradedComponents} degraded component(s): ${degradedNames}`);
    }
    healthDetails.push(`${healthyComponents}/${totalComponents} components healthy (${avgHealthScore.toFixed(0)}% avg health score)`);

    // Add error logs if significant
    if (equipmentSensor.error_log_count > 10) {
      healthDetails.push(`High error count: ${equipmentSensor.error_log_count} errors in last 24h`);
    }

    report.equipmentStatus.hardwareHealth = healthDetails.join('. ');

    // Add maintenance needs from degraded/critical components
    equipmentSensor.component_health.forEach(comp => {
      if (comp.status === 'critical' || comp.status === 'failed') {
        report.equipmentStatus.maintenanceNeeds.push(`URGENT: Replace/repair ${comp.component_name} (${Math.round(comp.health_score)}% health)`);
      } else if (comp.status === 'degraded') {
        report.equipmentStatus.maintenanceNeeds.push(`Schedule maintenance for ${comp.component_name} (${Math.round(comp.health_score)}% health)`);
      }
      // Check for components with low remaining life
      if (comp.estimated_remaining_life_days && comp.estimated_remaining_life_days <= 30) {
        report.equipmentStatus.endOfLifeWarnings.push(`${comp.component_name} has ~${comp.estimated_remaining_life_days} days remaining life`);
      } else if (comp.estimated_remaining_life_days && comp.estimated_remaining_life_days <= 60) {
        report.predictiveInsights.maintenanceRecommendations.push(`Plan replacement for ${comp.component_name} (~${comp.estimated_remaining_life_days} days remaining)`);
      }
    });

    // Firmware status from sensor data
    report.equipmentStatus.firmwareStatus = `Firmware: ${equipmentSensor.firmware_version}. ` +
      `Uptime: ${Math.floor(equipmentSensor.uptime_hours / 24)} days. ` +
      `Last reboot: ${toDate(equipmentSensor.last_reboot).toLocaleDateString()}`;
  } else {
    // Fallback if no sensor data
    report.equipmentStatus.hardwareHealth = node.status === 'healthy'
      ? 'Hardware operating within normal parameters (no sensor data available)'
      : `Hardware may need attention - node status is ${node.status} (no sensor data available)`;
    report.equipmentStatus.firmwareStatus = `Firmware ${node.firmware_version} - sensor data not available for detailed assessment`;
  }

  // Add antenna sensor data if available
  if (antennaSensor) {
    if (antennaSensor.mechanical_health < 70) {
      report.equipmentStatus.maintenanceNeeds.push(`Antenna mechanical health low: ${antennaSensor.mechanical_health}%`);
    }
    if (antennaSensor.motor_status !== 'operational') {
      report.equipmentStatus.maintenanceNeeds.push(`Antenna motor ${antennaSensor.motor_status}`);
    }
    if (Math.abs(antennaSensor.azimuth_drift) > 2 || Math.abs(antennaSensor.tilt_drift) > 1) {
      report.equipmentStatus.maintenanceNeeds.push(
        `Antenna calibration needed: azimuth drift ${antennaSensor.azimuth_drift.toFixed(1)}°, tilt drift ${antennaSensor.tilt_drift.toFixed(1)}°`
      );
    }
  }

  // Add environmental sensor data if available
  if (envSensor) {
    if (envSensor.power_quality < 80) {
      report.equipmentStatus.maintenanceNeeds.push(`Power quality issues: ${envSensor.power_quality}% stability`);
    }
    if (envSensor.backup_battery_level < 50) {
      report.equipmentStatus.maintenanceNeeds.push(`Low backup battery: ${envSensor.backup_battery_level}%`);
    }
    if (envSensor.cabinet_temperature > 45) {
      report.equipmentStatus.maintenanceNeeds.push(`Cabinet overheating: ${envSensor.cabinet_temperature}°C`);
    }
    if (envSensor.door_status !== 'closed') {
      report.equipmentStatus.maintenanceNeeds.push(`Security issue: cabinet door ${envSensor.door_status}`);
    }
  }
}
