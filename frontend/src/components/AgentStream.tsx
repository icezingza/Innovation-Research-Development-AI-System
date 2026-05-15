import React, { useEffect, useState, useRef } from 'react';

interface AgentLog {
  stage: 'semantic' | 'reasoning' | 'hypothesis' | 'feedback' | 'memory';
  message: string;
  timestamp: string;
}

export const AgentStream: React.FC = () => {
  const [logs, setLogs] = useState<AgentLog[]>([]);
  const eventSource = useRef<EventSource | null>(null);

  const connect = () => {
    // Replace with actual SSE endpoint
    eventSource.current = new EventSource('/api/v1/agents/stream');

    eventSource.current.onmessage = (event) => {
      try {
        const newLog = JSON.parse(event.data);
        setLogs((prev) => [...prev, newLog].slice(-50)); // Keep last 50 logs
      } catch (err) {
        console.error('Error parsing SSE data:', err);
      }
    };

    eventSource.current.onerror = () => {
      console.error('SSE connection failed, reconnecting...');
      eventSource.current?.close();
      setTimeout(connect, 3000);
    };
  };

  useEffect(() => {
    connect();
    return () => eventSource.current?.close();
  }, []);

  return (
    <div className="agent-stream-container" style={{ maxHeight: '400px', overflowY: 'auto', padding: '10px', background: '#1a1a1a', color: '#fff', borderRadius: '8px' }}>
      <h3>Agent Real-time Logs</h3>
      {logs.map((log, index) => (
        <div key={index} style={{ marginBottom: '5px', fontSize: '0.9em' }}>
          <span style={{ color: '#888' }}>[{log.timestamp}]</span>
          <span style={{ color: '#4CAF50', marginLeft: '5px' }}>{log.stage.toUpperCase()}:</span>
          <span style={{ marginLeft: '5px' }}>{log.message}</span>
        </div>
      ))}
    </div>
  );
};
