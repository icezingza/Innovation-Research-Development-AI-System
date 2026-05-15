var __assign = (this && this.__assign) || function () {
    __assign = Object.assign || function(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
            s = arguments[i];
            for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p))
                t[p] = s[p];
        }
        return t;
    };
    return __assign.apply(this, arguments);
};
import { useEffect } from 'react';
import { useDashboardStore } from '../store/useDashboardStore';
import { getWorkflowStream } from '../api/apiClient';
export var useWorkflowStream = function (workflowId) {
    var _a = useDashboardStore(), addEvent = _a.addEvent, setReconnectStatus = _a.setReconnectStatus;
    useEffect(function () {
        if (!workflowId)
            return;
        setReconnectStatus('connecting');
        var eventSource = getWorkflowStream(workflowId);
        eventSource.onopen = function () {
            setReconnectStatus('connected');
        };
        eventSource.onmessage = function (event) {
            try {
                var data = JSON.parse(event.data);
                addEvent(__assign({ id: Date.now().toString(), timestamp: new Date().toISOString() }, data));
            }
            catch (error) {
                console.error('Error parsing SSE message:', error);
            }
        };
        eventSource.onerror = function () {
            setReconnectStatus('disconnected');
            eventSource.close();
        };
        return function () {
            eventSource.close();
            setReconnectStatus('disconnected');
        };
    }, [workflowId, addEvent, setReconnectStatus]);
};
