import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

interface DataPoint {
  [key: string]: string | number;
}

interface ChatDataChartProps {
  data: DataPoint[];
  xKey: string;
  yKey: string;
  title?: string;
}

const ChatDataChart: React.FC<ChatDataChartProps> = ({ data, xKey, yKey, title }) => {
  return (
    <div style={{ width: '100%', height: 300, marginTop: '1rem', marginBottom: '1rem' }}>
      {title && (
        <h4 style={{ textAlign: 'center', marginBottom: '1rem' }}>{title}</h4>
      )}
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{
            top: 5,
            right: 30,
            left: 20,
            bottom: 5,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={xKey} />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey={yKey} fill="#8884d8" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ChatDataChart; 