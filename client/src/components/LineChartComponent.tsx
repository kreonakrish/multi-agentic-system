import React from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

type Props = {
  data: any[];
};

const LineChartComponent: React.FC<Props> = ({ data }) => (
  <ResponsiveContainer width="100%" height={250}>
    <LineChart data={data}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey="name" />
      <YAxis />
      <Tooltip />
      <Legend />
      <Line type="monotone" dataKey="sent" stroke="#8884d8" />
      <Line type="monotone" dataKey="received" stroke="#82ca9d" />
    </LineChart>
  </ResponsiveContainer>
);

export default LineChartComponent;