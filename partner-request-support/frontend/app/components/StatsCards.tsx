'use client';

import { motion } from 'framer-motion';
import { FileSpreadsheet, CheckCircle2, Database, Globe } from 'lucide-react';
import { ProcessingStats } from '../types';

interface StatsCardsProps {
  stats: ProcessingStats | undefined | null;
}

interface StatCardProps {
  title: string;
  value: number;
  percentage?: number;
  subtitle?: string;
  color: string;
  icon: React.ReactNode;
}

const StatCard = ({ title, value, percentage, subtitle, color, icon }: StatCardProps) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4 }}
      transition={{ duration: 0.3 }}
      style={{
        background: 'white',
        padding: 'var(--space-md)',
        borderRadius: 'var(--radius-md)',
        boxShadow: 'var(--shadow-sm)',
        borderTop: `3px solid ${color}`,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
        <div>
          <p
            style={{
              color: 'var(--color-text-muted)',
              fontSize: '0.75rem',
              fontWeight: 500,
              marginBottom: '4px',
            }}
          >
            {title}
          </p>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
            <h3
              style={{
                fontSize: '1.75rem',
                fontWeight: 700,
                color,
                lineHeight: 1,
              }}
            >
              {value}
            </h3>
            {percentage !== undefined && (
              <span
                style={{
                  color: 'var(--color-text-muted)',
                  fontSize: '0.875rem',
                  fontWeight: 500,
                }}
              >
                ({percentage}%)
              </span>
            )}
          </div>
          {subtitle && (
            <p
              style={{ fontSize: '0.6875rem', color: 'var(--color-text-muted)', marginTop: '2px' }}
            >
              {subtitle}
            </p>
          )}
        </div>
        <div
          style={{
            width: '36px',
            height: '36px',
            background: `${color}15`,
            borderRadius: 'var(--radius-sm)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color,
          }}
        >
          {icon}
        </div>
      </div>
    </motion.div>
  );
};

export const StatsCards = ({ stats }: StatsCardsProps) => {
  if (!stats) return null;
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: 'var(--space-sm)',
        marginBottom: 'var(--space-lg)',
      }}
    >
      <StatCard
        title="Total Partners"
        value={stats.total}
        color="var(--cgiar-navy)"
        icon={<FileSpreadsheet size={20} />}
      />
      <StatCard
        title="Matched"
        value={stats.matched}
        percentage={stats.matched_percentage}
        color="var(--cgiar-green)"
        icon={<CheckCircle2 size={20} />}
      />
      <StatCard
        title="Excellent Matches"
        value={stats.excellent}
        color="var(--color-excellent)"
        icon={<Database size={20} />}
      />
      <StatCard
        title="Web Searches"
        value={stats.web_search_success}
        subtitle={`${stats.web_search_attempted} attempted`}
        color="var(--cgiar-blue)"
        icon={<Globe size={20} />}
      />
    </div>
  );
};
