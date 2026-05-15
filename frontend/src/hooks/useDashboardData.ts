import { useQuery } from '@tanstack/react-query';
import { getCognitionStatus } from '../api/apiClient';

export const useDashboardData = () => {
  return useQuery({
    queryKey: ['dashboardData'],
    queryFn: getCognitionStatus,
    refetchInterval: 5000, // Poll every 5 seconds for static updates
  });
};
