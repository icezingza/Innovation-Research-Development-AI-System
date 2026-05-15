import { useQuery } from '@tanstack/react-query';
import { getCognitionStatus } from '../api/apiClient';
export var useDashboardData = function () {
    return useQuery({
        queryKey: ['dashboardData'],
        queryFn: getCognitionStatus,
        refetchInterval: 5000, // Poll every 5 seconds for static updates
    });
};
