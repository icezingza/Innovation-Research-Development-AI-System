import { create } from 'zustand';

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

const MAX_EVENTS = 50;

export const useDashboardStore = create<DashboardState & DashboardActions>((set) => ({
  eventCapping: [],
  reconnectStatus: 'disconnected',
  activeWorkflowId: null,

  addEvent: (event) =>
    set((state) => ({
      eventCapping: [event, ...state.eventCapping].slice(0, MAX_EVENTS),
    })),

  setReconnectStatus: (status) => set({ reconnectStatus: status }),

  setActiveWorkflowId: (id) => set({ activeWorkflowId: id }),

  clearEvents: () => set({ eventCapping: [] }),
}));
