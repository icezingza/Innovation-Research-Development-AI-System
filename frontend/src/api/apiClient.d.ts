import { CoordinatedResult } from '../types';
declare const apiClient: import("axios").AxiosInstance;
export declare const getCognitionStatus: () => Promise<any>;
export declare const coordinateCognition: (goal: string) => Promise<CoordinatedResult>;
export declare const getWorkflowStream: (id: string) => EventSource;
export default apiClient;
