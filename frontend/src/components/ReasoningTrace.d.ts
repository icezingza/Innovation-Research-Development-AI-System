import React from 'react';
interface TraceData {
    generation: number;
    score: number;
    [key: string]: number;
}
interface ReasoningTraceProps {
    data: TraceData[];
}
export declare const ReasoningTrace: React.FC<ReasoningTraceProps>;
export {};
