import React from "react";
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";

interface PieChartComponentProps {
  data: { name: string; value: number }[];
  height?: number;
}

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#A28CFF", "#FF6699"];

const PieChartComponent: React.FC<PieChartComponentProps> = ({ data, height = 220 }) => (
  <ResponsiveContainer width="100%" height={height}>
    <PieChart>
      <Pie
        data={data}
        dataKey="value"
        nameKey="name"
        cx="50%"
        cy="50%"
        outerRadius={70}
        fill="#8884d8"
        label
      >
        {data.map((entry, index) => (
          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
        ))}
      </Pie>
      <Tooltip />
      <Legend />
    </PieChart>
  </ResponsiveContainer>
);

export default PieChartComponent;

