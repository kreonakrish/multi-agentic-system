import React from 'react';
import { Bar } from 'react-chartjs-2';
import { barChartOptions } from '../../config/chartConfig';

interface BarChartProps {
  data: {
    labels: string[];
    datasets: {
      label: string;
      data: number[];
      backgroundColor: string | string[];
      borderColor: string | string[];
      borderWidth: number;
    }[];
  };
}

const BarChartComponent: React.FC<BarChartProps> = ({ data }) => {
  return (
    <div style={{ height: '300px', width: '100%' }}>
      <Bar data={data} options={barChartOptions} />
    </div>
  );
};

export default BarChartComponent; 