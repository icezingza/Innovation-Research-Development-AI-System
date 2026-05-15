interface DashboardEvent {
    id: string;
    timestamp: string;
    message: string;
    [key: string]: any;
}
interface DashboardState {
    eventCapping: DashboardEvent[];
    reconnectStatus: 'connected' | 'disconnected' | 'connecting';
    activeWorkflowId: string | null;
}
interface DashboardActions {
    addEvent: (event: DashboardEvent) => void;
    setReconnectStatus: (status: DashboardState['reconnectStatus']) => void;
    setActiveWorkflowId: (id: string | null) => void;
    clearEvents: () => void;
}
export declare const useDashboardStore: import("zustand").UseBoundStore<import("zustand").StoreApi<DashboardState & DashboardActions>>;
export {};
