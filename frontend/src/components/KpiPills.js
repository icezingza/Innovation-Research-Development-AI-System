import React from 'react';
import { useDashboardStore } from '../store/useDashboardStore';
import './KpiPills.css';
var KpiPills = function () {
    var _a = useDashboardStore(), eventCapping = _a.eventCapping, reconnectStatus = _a.reconnectStatus;
    var activeAgents = eventCapping.filter(function (e) { return e.type === 'agent_update'; }).length;
    var avgConfidence = eventCapping.length > 0
        ? (eventCapping.reduce(function (acc, curr) { return acc + (curr.confidence || 0); }, 0) / eventCapping.length).toFixed(2)
        : '0.00';
    return (<div className="kpi-container">
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
        <span className={"kpi-value status-".concat(reconnectStatus)}>{reconnectStatus}</span>
      </div>
    </div>);
};
export default KpiPills;
