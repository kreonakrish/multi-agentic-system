import React from 'react';
import { Line } from 'react-chartjs-2';
import { chartOptions } from '../../config/chartConfig';

interface LineChartProps {
  data: {
    labels: string[];
    datasets: {
      label: string;
      data: number[];
      borderColor: string;
      backgroundColor: string;
      tension: number;
    }[];
  };
}

const LineChartComponent: React.FC<LineChartProps> = ({ data }) => {
  return (
    <div style={{ height: '300px', width: '100%' }}>
      <Line data={data} options={chartOptions} />
    </div>
  );
};

export default LineChartComponent; 