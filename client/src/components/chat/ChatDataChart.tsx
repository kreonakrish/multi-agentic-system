import React from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
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

// Colors for pie chart segments and bars
const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff8042', '#a4de6c', '#d0ed57'];

const ChatDataChart: React.FC<ChatDataChartProps> = ({ data, xKey, yKey, title }) => {
  // Function to determine the best chart type based on data characteristics
  const determineChartType = () => {
    // If we have 2 or fewer data points, use a pie chart
    if (data.length <= 2) {
      return 'pie';
    }

    // Check if x-axis values are dates
    const isTimeData = data.every(item => !isNaN(Date.parse(String(item[xKey]))));
    if (isTimeData) {
      return 'line';
    }

    // Check if there's a clear trend (monotonic increase/decrease)
    const values = data.map(item => Number(item[yKey]));
    const isMonotonic = values.every((val, i) => i === 0 || val >= values[i - 1]) ||
                       values.every((val, i) => i === 0 || val <= values[i - 1]);
    if (isMonotonic && data.length > 3) {
      return 'line';
    }

    // Check if we're comparing parts of a whole
    const total = values.reduce((sum, val) => sum + val, 0);
    const arePercentages = values.every(val => val >= 0 && val <= 100) &&
                          Math.abs(values.reduce((sum, val) => sum + val, 0) - 100) < 0.1;
    if (arePercentages || (values.every(val => val >= 0) && data.length <= 5)) {
      return 'pie';
    }

    // Default to bar chart for categorical comparisons
    return 'bar';
  };

  const chartType = determineChartType();

  const renderChart = () => {
    switch (chartType) {
      case 'pie':
        return (
          <PieChart>
            <Pie
              data={data}
              dataKey={yKey}
              nameKey={xKey}
              cx="50%"
              cy="50%"
              outerRadius={80}
              label
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        );

      case 'line':
        return (
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={xKey} />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line
              type="monotone"
              dataKey={yKey}
              stroke="#8884d8"
              activeDot={{ r: 8 }}
            />
          </LineChart>
        );

      default: // Bar chart
        return (
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={xKey} />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey={yKey} fill="#8884d8">
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        );
    }
  };

  return (
    <div style={{ width: '100%', height: 300, marginTop: '1rem', marginBottom: '1rem' }}>
      {title && (
        <h4 style={{ textAlign: 'center', marginBottom: '1rem' }}>
          {title} ({chartType.charAt(0).toUpperCase() + chartType.slice(1)} Chart)
        </h4>
      )}
      <ResponsiveContainer width="100%" height="100%">
        {renderChart()}
      </ResponsiveContainer>
    </div>
  );
};

export default ChatDataChart; 