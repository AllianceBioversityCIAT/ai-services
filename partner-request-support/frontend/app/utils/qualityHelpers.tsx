import { CheckCircle2, XCircle } from 'lucide-react';
import { MatchQuality } from '../types/partner.types';

export const getQualityColor = (quality: MatchQuality): string => {
  switch (quality) {
    case 'excellent':
      return 'var(--color-excellent)';
    case 'good':
      return 'var(--color-good)';
    case 'fair':
      return 'var(--color-fair)';
    case 'no_match':
      return 'var(--color-no-match)';
    case 'error':
      return 'var(--color-error)';
    default:
      return 'var(--color-error)';
  }
};

export const getQualityBadge = (quality: MatchQuality): { label: string; icon: React.ReactNode } => {
  const config: Record<MatchQuality, { label: string; icon: React.ReactNode }> = {
    excellent: { label: 'Excellent', icon: <CheckCircle2 size={16} /> },
    good: { label: 'Good', icon: <CheckCircle2 size={16} /> },
    fair: { label: 'Fair', icon: <CheckCircle2 size={16} /> },
    no_match: { label: 'No Match', icon: <XCircle size={16} /> },
    error: { label: 'Error', icon: <XCircle size={16} /> },
  };
  return config[quality];
};
