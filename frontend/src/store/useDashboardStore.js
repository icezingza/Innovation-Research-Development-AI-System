var __spreadArray = (this && this.__spreadArray) || function (to, from, pack) {
    if (pack || arguments.length === 2) for (var i = 0, l = from.length, ar; i < l; i++) {
        if (ar || !(i in from)) {
            if (!ar) ar = Array.prototype.slice.call(from, 0, i);
            ar[i] = from[i];
        }
    }
    return to.concat(ar || Array.prototype.slice.call(from));
};
import { create } from 'zustand';
var MAX_EVENTS = 50;
export var useDashboardStore = create(function (set) { return ({
    eventCapping: [],
    reconnectStatus: 'disconnected',
    activeWorkflowId: null,
    addEvent: function (event) {
        return set(function (state) { return ({
            eventCapping: __spreadArray([event], state.eventCapping, true).slice(0, MAX_EVENTS),
        }); });
    },
    setReconnectStatus: function (status) { return set({ reconnectStatus: status }); },
    setActiveWorkflowId: function (id) { return set({ activeWorkflowId: id }); },
    clearEvents: function () { return set({ eventCapping: [] }); },
}); });
