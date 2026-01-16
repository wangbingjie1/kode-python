'use client';

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';

interface Campaign {
  name: string;
  impressions: string;
  clicks: string;
  conversion: string;
  roi: string;
  status: 'Active' | 'Warning' | 'Inactive';
  progress: number;
}

export default function BiDashboardPage() {
  const searchParams = useSearchParams();
  const template = searchParams?.get('template');
  const [lastUpdated, setLastUpdated] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => {
      setLastUpdated(new Date());
    }, 60000);
    return () => clearInterval(interval);
  }, []);

  const templateTitles: Record<string, string> = {
    'freeform': '自定义视图',
    'analytics': '分析仪表板',
    'monitor': '监控仪表板',
    'report': '报告生成器',
    'goals': '目标跟踪',
    'sales': '销售漏斗',
    'users': '用户分析',
    'financial': '财务概览',
    'marketing': '营销表现',
    'product': '产品指标'
  };

  const title = template ? (templateTitles[template] || '仪表板') : '分析仪表板';

  const campaigns: Campaign[] = [
    {
      name: '2024夏季促销',
      impressions: '120万',
      clicks: '4.53万',
      conversion: '12.5%',
      roi: '3.2倍',
      status: 'Active',
      progress: 85
    },
    {
      name: 'Q2邮件营销',
      impressions: '85.6万',
      clicks: '3.21万',
      conversion: '9.8%',
      roi: '2.8倍',
      status: 'Active',
      progress: 72
    },
    {
      name: '社交媒体广告',
      impressions: '210万',
      clicks: '7.85万',
      conversion: '7.2%',
      roi: '2.1倍',
      status: 'Warning',
      progress: 58
    },
    {
      name: '产品发布活动',
      impressions: '64.5万',
      clicks: '2.89万',
      conversion: '15.3%',
      roi: '4.5倍',
      status: 'Active',
      progress: 92
    },
    {
      name: '再营销活动',
      impressions: '42.3万',
      clicks: '1.92万',
      conversion: '11.5%',
      roi: '3.6倍',
      status: 'Active',
      progress: 78
    },
    {
      name: '2023遗留活动',
      impressions: '18.9万',
      clicks: '5.2千',
      conversion: '2.8%',
      roi: '0.9倍',
      status: 'Inactive',
      progress: 15
    }
  ];

  return (
    <div className="min-h-screen bg-[#F7F8F9]">
      {/* Header */}
      <div className="bg-white border-b border-[#E2E8F0] px-10 py-5 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <span className="text-3xl">📊</span>
          <div>
            <h1 className="text-2xl font-semibold text-[#1A202C]">{title}</h1>
            <p className="text-sm text-[#718096] mt-1">
              最后更新: {lastUpdated.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          <button className="px-5 py-2.5 rounded-lg bg-[#F7F8F9] text-[#4A5568] text-sm font-medium transition-all hover:bg-[#E2E8F0]">
            ⚙️ 设置
          </button>
          <button className="px-5 py-2.5 rounded-lg bg-[#F7F8F9] text-[#4A5568] text-sm font-medium transition-all hover:bg-[#E2E8F0]">
            📤 导出
          </button>
          <button className="px-5 py-2.5 rounded-lg bg-[#7AB8CC] text-white text-sm font-medium transition-all hover:bg-[#5A95A8]">
            🔄 刷新
          </button>
        </div>
      </div>

      <div className="max-w-[1400px] mx-auto px-10 py-10">
        {/* KPI Metrics */}
        <div className="grid grid-cols-4 gap-5 mb-10">
          <MetricCard
            label="总收入"
            value="$1.24M"
            change="+18.2%"
            trend="up"
          />
          <MetricCard
            label="活跃用户"
            value="45.9K"
            change="+12.5%"
            trend="up"
          />
          <MetricCard
            label="转化率"
            value="10.7%"
            change="+2.3%"
            trend="up"
          />
          <MetricCard
            label="平均订单价值"
            value="$52.85"
            change="-3.1%"
            trend="down"
          />
        </div>

        {/* Charts Section */}
        <div className="grid grid-cols-[2fr_1fr] gap-5 mb-10">
          <ChartCard
            title="收入趋势（最近30天）"
            description="📈 交互式图表: 收入从 $890K 增长到 $1.24M"
          />
          <ChartCard
            title="流量来源"
            description="🥧 饼图: 自然流量: 45% | 直接访问: 28% | 社交媒体: 18% | 邮件: 9%"
            compact
          />
        </div>

        {/* Data Table */}
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-6">
          <div className="flex justify-between items-center mb-5">
            <h3 className="text-lg font-semibold text-[#1A202C]">表现最佳的活动</h3>
            <input
              type="search"
              placeholder="搜索..."
              className="px-4 py-2 border border-[#E2E8F0] rounded-lg text-sm"
            />
          </div>
          <table className="w-full">
            <thead>
              <tr className="border-b-2 border-[#E2E8F0]">
                <th className="text-left py-3 px-3 text-xs text-[#718096] font-semibold uppercase tracking-wider">活动名称</th>
                <th className="text-left py-3 px-3 text-xs text-[#718096] font-semibold uppercase tracking-wider">展示量</th>
                <th className="text-left py-3 px-3 text-xs text-[#718096] font-semibold uppercase tracking-wider">点击量</th>
                <th className="text-left py-3 px-3 text-xs text-[#718096] font-semibold uppercase tracking-wider">转化率</th>
                <th className="text-left py-3 px-3 text-xs text-[#718096] font-semibold uppercase tracking-wider">投资回报率</th>
                <th className="text-left py-3 px-3 text-xs text-[#718096] font-semibold uppercase tracking-wider">状态</th>
                <th className="text-left py-3 px-3 text-xs text-[#718096] font-semibold uppercase tracking-wider">进度</th>
              </tr>
            </thead>
            <tbody>
              {campaigns.map((campaign, index) => (
                <tr key={index} className="border-b border-[#E2E8F0] hover:bg-[#F7F8F9] transition-colors">
                  <td className="py-4 px-3 text-sm"><strong>{campaign.name}</strong></td>
                  <td className="py-4 px-3 text-sm">{campaign.impressions}</td>
                  <td className="py-4 px-3 text-sm">{campaign.clicks}</td>
                  <td className="py-4 px-3 text-sm">{campaign.conversion}</td>
                  <td className="py-4 px-3 text-sm">{campaign.roi}</td>
                  <td className="py-4 px-3 text-sm">
                    <StatusBadge status={campaign.status} />
                  </td>
                  <td className="py-4 px-3 text-sm">
                    <ProgressBar progress={campaign.progress} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value, change, trend }: {
  label: string;
  value: string;
  change: string;
  trend: 'up' | 'down';
}) {
  return (
    <div className="bg-white border border-[#E2E8F0] rounded-xl p-6 transition-all hover:shadow-md hover:-translate-y-0.5">
      <div className="text-xs text-[#718096] uppercase tracking-wide mb-2">{label}</div>
      <div className="text-[32px] font-bold text-[#1A202C] mb-2">{value}</div>
      <div className={`text-sm font-medium flex items-center gap-1 ${
        trend === 'up' ? 'text-[#48BB78]' : 'text-[#F56565]'
      }`}>
        <span>{trend === 'up' ? '↑' : '↓'}</span>
        <span>{change} vs 上月</span>
      </div>
    </div>
  );
}

function ChartCard({ title, description, compact }: {
  title: string;
  description: string;
  compact?: boolean;
}) {
  return (
    <div className="bg-white border border-[#E2E8F0] rounded-xl p-6">
      <div className="flex justify-between items-center mb-5">
        <h3 className="text-lg font-semibold text-[#1A202C]">{title}</h3>
        {!compact && (
          <select className="px-3 py-1.5 bg-[#F7F8F9] text-[#4A5568] text-sm rounded-lg border-0">
            <option>最近30天</option>
            <option>最近7天</option>
            <option>最近90天</option>
          </select>
        )}
      </div>
      <div className={`${compact ? 'h-[300px]' : 'h-[300px]'} bg-gradient-to-br from-[#f5f7fa] to-[#c3cfe2] rounded-lg flex items-center justify-center text-[#718096] text-sm whitespace-pre-line text-center p-4`}>
        {description}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: 'Active' | 'Warning' | 'Inactive' }) {
  const styles = {
    Active: 'bg-[#C6F6D5] text-[#22543D]',
    Warning: 'bg-[#FEEBC8] text-[#7C2D12]',
    Inactive: 'bg-[#FED7D7] text-[#742A2A]'
  };

  return (
    <span className={`px-3 py-1 rounded-xl text-xs font-medium ${styles[status]}`}>
      {status === 'Active' ? '活跃' : status === 'Warning' ? '警告' : '非活跃'}
    </span>
  );
}

function ProgressBar({ progress }: { progress: number }) {
  return (
    <div className="w-full h-2 bg-[#F7F8F9] rounded-full overflow-hidden">
      <div
        className="h-full bg-gradient-to-r from-[#7AB8CC] to-[#5A95A8] rounded-full transition-all duration-300"
        style={{ width: `${progress}%` }}
      />
    </div>
  );
}
