import React from 'react';
import { Pie } from 'react-chartjs-2';
import { pieChartOptions } from '../../config/chartConfig';

interface PieChartProps {
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

const PieChartComponent: React.FC<PieChartProps> = ({ data }) => {
  return (
    <div style={{ height: '300px', width: '100%' }}>
      <Pie data={data} options={pieChartOptions} />
    </div>
  );
};

export default PieChartComponent; 