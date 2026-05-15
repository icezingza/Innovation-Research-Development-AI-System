import axios from 'axios';
import { CoordinatedResult } from '../types';

const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getCognitionStatus = async () => {
  const response = await apiClient.get('/cognition/status');
  return response.data;
};

export const coordinateCognition = async (goal: string): Promise<CoordinatedResult> => {
  const response = await apiClient.post('/cognition/coordinate', { goal });
  return response.data;
};

export const getWorkflowStream = (id: string): EventSource => {
  return new EventSource(`http://localhost:8000/streams/workflows/${id}`);
};

export default apiClient;
