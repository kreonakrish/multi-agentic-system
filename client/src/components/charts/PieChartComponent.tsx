import React from 'react';
import { Pie } from 'react-chartjs-2';
import { chartOptions } from '../../config/chartConfig';

interface PieChartProps {
  data: {
    labels: string[];
    datasets: {
      label: string;
      data: number[];
      backgroundColor: string[];
      borderColor: string[];
      borderWidth: number;
    }[];
  };
}

const PieChartComponent: React.FC<PieChartProps> = ({ data }) => {
  return (
    <div style={{ height: '300px', width: '100%' }}>
      <Pie data={data} options={chartOptions} />
    </div>
  );
};

export default PieChartComponent; 