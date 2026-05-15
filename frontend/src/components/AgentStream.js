var __spreadArray = (this && this.__spreadArray) || function (to, from, pack) {
    if (pack || arguments.length === 2) for (var i = 0, l = from.length, ar; i < l; i++) {
        if (ar || !(i in from)) {
            if (!ar) ar = Array.prototype.slice.call(from, 0, i);
            ar[i] = from[i];
        }
    }
    return to.concat(ar || Array.prototype.slice.call(from));
};
import React, { useEffect, useState, useRef } from 'react';
export var AgentStream = function () {
    var _a = useState([]), logs = _a[0], setLogs = _a[1];
    var eventSource = useRef(null);
    var connect = function () {
        // Replace with actual SSE endpoint
        eventSource.current = new EventSource('/api/v1/agents/stream');
        eventSource.current.onmessage = function (event) {
            try {
                var newLog_1 = JSON.parse(event.data);
                setLogs(function (prev) { return __spreadArray(__spreadArray([], prev, true), [newLog_1], false).slice(-50); }); // Keep last 50 logs
            }
            catch (err) {
                console.error('Error parsing SSE data:', err);
            }
        };
        eventSource.current.onerror = function () {
            var _a;
            console.error('SSE connection failed, reconnecting...');
            (_a = eventSource.current) === null || _a === void 0 ? void 0 : _a.close();
            setTimeout(connect, 3000);
        };
    };
    useEffect(function () {
        connect();
        return function () { var _a; return (_a = eventSource.current) === null || _a === void 0 ? void 0 : _a.close(); };
    }, []);
    return (<div className="agent-stream-container" style={{ maxHeight: '400px', overflowY: 'auto', padding: '10px', background: '#1a1a1a', color: '#fff', borderRadius: '8px' }}>
      <h3>Agent Real-time Logs</h3>
      {logs.map(function (log, index) { return (<div key={index} style={{ marginBottom: '5px', fontSize: '0.9em' }}>
          <span style={{ color: '#888' }}>[{log.timestamp}]</span>
          <span style={{ color: '#4CAF50', marginLeft: '5px' }}>{log.stage.toUpperCase()}:</span>
          <span style={{ marginLeft: '5px' }}>{log.message}</span>
        </div>); })}
    </div>);
};
