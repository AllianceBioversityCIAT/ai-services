'use client';

import { MatchQuality } from '../types/partner.types';
import { getQualityBadge, getQualityColor } from '../utils/qualityHelpers';

interface QualityBadgeProps {
  quality: MatchQuality;
}

export const QualityBadge = ({ quality }: QualityBadgeProps) => {
  const badge = getQualityBadge(quality);
  const color = getQualityColor(quality);

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '4px 12px',
        borderRadius: 'var(--radius-full)',
        background: `${color}20`,
        color: color,
        fontSize: '0.8125rem',
        fontWeight: 600,
      }}
    >
      {badge.icon}
      {badge.label}
    </div>
  );
};
