import { useEffect } from 'react';
import { useDashboardStore } from '../store/useDashboardStore';
import { getWorkflowStream } from '../api/apiClient';

export const useWorkflowStream = (workflowId: string | null) => {
  const { addEvent, setReconnectStatus } = useDashboardStore();

  useEffect(() => {
    if (!workflowId) return;

    setReconnectStatus('connecting');
    const eventSource = getWorkflowStream(workflowId);

    eventSource.onopen = () => {
      setReconnectStatus('connected');
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        addEvent({
          id: Date.now().toString(),
          timestamp: new Date().toISOString(),
          ...data
        });
      } catch (error) {
        console.error('Error parsing SSE message:', error);
      }
    };

    eventSource.onerror = () => {
      setReconnectStatus('disconnected');
      eventSource.close();
    };

    return () => {
      eventSource.close();
      setReconnectStatus('disconnected');
    };
  }, [workflowId, addEvent, setReconnectStatus]);
};
