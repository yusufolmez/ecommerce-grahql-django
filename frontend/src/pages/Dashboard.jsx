import React from "react";
import { DollarSign, ShoppingBag, Eye } from "lucide-react";
import "../index.css";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

function Dashboard() {
  const salesData = [
    { month: "Jan", sales: 250 },
    { month: "Feb", sales: 320 },
    { month: "Mar", sales: 300 },
    // ... diğer aylar
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Overview</h1>
        <select className="px-4 py-2 border border-gray-200 rounded-lg bg-white">
          <option>Monthly</option>
          <option>Weekly</option>
        </select>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-3 gap-6 mb-6">
        <div className="bg-white p-6 rounded-xl shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-gray-500">Total profit</h3>
            <div className="p-2 bg-blue-100 rounded-full">
              <DollarSign size={20} className="text-blue-600" />
            </div>
          </div>
          <div className="flex items-end gap-2">
            <span className="text-2xl font-semibold">$82,373.21</span>
            <span className="text-green-500 text-sm">+3.4%</span>
          </div>
          <p className="text-sm text-gray-500 mt-1">from last month</p>
        </div>
        {/* Diğer metrik kartları... */}
      </div>

      {/* Chart */}
      <div className="bg-white p-6 rounded-xl shadow-sm">
        <LineChart width={800} height={300} data={salesData}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="month" />
          <YAxis />
          <Tooltip />
          <Line
            type="monotone"
            dataKey="sales"
            stroke="#2563eb"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </div>
    </div>
  );
}

export default Dashboard;
