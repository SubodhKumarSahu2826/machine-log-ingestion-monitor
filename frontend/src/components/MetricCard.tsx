import React from 'react';

interface MetricCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  icon?: React.ReactNode;
  valueColor?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  valueColor,
}) => {
  return (
    <div className="metric-card">
      <div className="metric-title">
        <span>{title}</span>
        {icon && <span>{icon}</span>}
      </div>
      <div className="metric-value" style={{ color: valueColor || '#fff' }}>
        {value}
      </div>
      {subtitle && <div className="metric-subtitle">{subtitle}</div>}
    </div>
  );
};
