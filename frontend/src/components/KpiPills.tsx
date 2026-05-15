import React from 'react';
import { useDashboardStore } from '../store/useDashboardStore';
import './KpiPills.css';

const KpiPills: React.FC = () => {
  const { eventCapping, reconnectStatus } = useDashboardStore();

  const activeAgents = eventCapping.filter(e => e.type === 'agent_update').length;
  const avgConfidence = eventCapping.length > 0 
    ? (eventCapping.reduce((acc, curr) => acc + (curr.confidence || 0), 0) / eventCapping.length).toFixed(2)
    : '0.00';

  return (
    <div className="kpi-container">
      <div className="kpi-pill">
        <span className="kpi-label">Active Agents</span>
        <span className="kpi-value">{activeAgents}</span>
      </div>
      <div className="kpi-pill">
        <span className="kpi-label">Avg Confidence</span>
        <span className="kpi-value">{avgConfidence}</span>
      </div>
      <div className="kpi-pill">
        <span className="kpi-label">System Status</span>
        <span className={`kpi-value status-${reconnectStatus}`}>{reconnectStatus}</span>
      </div>
    </div>
  );
};

export default KpiPills;
