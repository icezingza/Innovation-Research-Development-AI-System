import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

interface TraceData {
  generation: number;
  score: number;
  [key: string]: number;
}

interface ReasoningTraceProps {
  data: TraceData[];
}

export const ReasoningTrace: React.FC<ReasoningTraceProps> = ({ data }) => {
  return (
    <div style={{ width: '100%', height: 400, backgroundColor: '#f9f9f9', padding: '1rem', borderRadius: '8px' }}>
      <h3 style={{ textAlign: 'center', marginBottom: '1rem' }}>Reasoning Evolution Trace</h3>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="generation" label={{ value: 'Generation', position: 'insideBottomRight', offset: -10 }} />
          <YAxis label={{ value: 'Score', angle: -90, position: 'insideLeft' }} />
          <Tooltip />
          <Legend />
          <Line
            type="monotone"
            dataKey="score"
            stroke="#8884d8"
            strokeWidth={3}
            activeDot={{ r: 8 }}
            name="Hypothesis Score"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};
