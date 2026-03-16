"use client";

import { Info, CheckCircle, AlertCircle } from "lucide-react";

interface SyncInfo {
  sync_performed: boolean;
  institutions_before: number;
  institutions_after: number;
  new_institutions: number;
  modified_institutions: number;
  unchanged_institutions: number;
  total_processed: number;
  sync_message: string;
}

interface SyncAlertProps {
  syncInfo: SyncInfo;
  className?: string;
}

export function SyncAlert({ syncInfo, className = "" }: SyncAlertProps) {
  // Don't show if no changes
  if (syncInfo.total_processed === 0) {
    return null;
  }

  // Determine alert style based on number of changes
  const isSignificant = syncInfo.total_processed > 10;

  return (
    <div
      className={className}
      style={{
        display: 'flex',
        alignItems: 'start',
        gap: '12px',
        padding: '16px',
        background: isSignificant ? '#FFFBF0' : '#F0F7FC',
        border: `1px solid ${isSignificant ? '#FFE8A3' : '#D4E7F4'}`,
        borderLeft: `4px solid ${isSignificant ? 'var(--cgiar-yellow)' : 'var(--cgiar-blue)'}`,
        borderRadius: '8px',
        marginBottom: '16px',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      {isSignificant ? (
        <AlertCircle 
          size={20} 
          style={{ 
            color: 'var(--cgiar-yellow)', 
            marginTop: '2px', 
            flexShrink: 0 
          }} 
        />
      ) : (
        <Info 
          size={20} 
          style={{ 
            color: 'var(--cgiar-blue)', 
            marginTop: '2px', 
            flexShrink: 0 
          }} 
        />
      )}
      <div style={{ flex: 1 }}>
        <h4
          style={{
            fontSize: '0.875rem',
            fontWeight: 600,
            color: 'var(--cgiar-navy)',
            marginBottom: '4px',
          }}
        >
          Database Updated
        </h4>
        <p
          style={{
            fontSize: '0.8125rem',
            marginTop: '4px',
            color: 'var(--color-text-secondary)',
            lineHeight: 1.5,
          }}
        >
          {syncInfo.sync_message}
        </p>
        <div style={{ 
          marginTop: '8px', 
          display: 'flex', 
          flexWrap: 'wrap', 
          gap: '8px' 
        }}>
          {syncInfo.new_institutions > 0 && (
            <span
              style={{
                fontSize: '0.75rem',
                padding: '4px 8px',
                borderRadius: '4px',
                background: isSignificant ? '#FFF4E6' : '#E6F3FF',
                color: isSignificant ? '#B7791F' : '#004080',
                fontWeight: 500,
              }}
            >
              +{syncInfo.new_institutions} new
            </span>
          )}
          {syncInfo.modified_institutions > 0 && (
            <span
              style={{
                fontSize: '0.75rem',
                padding: '4px 8px',
                borderRadius: '4px',
                background: isSignificant ? '#FFF4E6' : '#E6F3FF',
                color: isSignificant ? '#B7791F' : '#004080',
                fontWeight: 500,
              }}
            >
              {syncInfo.modified_institutions} modified
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

interface SyncBadgeProps {
  totalProcessed: number;
  className?: string;
}

export function SyncBadge({ totalProcessed, className = "" }: SyncBadgeProps) {
  if (totalProcessed === 0) {
    return (
      <span
        className={className}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          padding: '4px 8px',
          fontSize: '0.75rem',
          background: '#E8F5E9',
          color: 'var(--cgiar-green)',
          borderRadius: '4px',
          fontWeight: 500,
        }}
      >
        <CheckCircle size={12} />
        Up to date
      </span>
    );
  }

  return (
    <span
      className={className}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        padding: '4px 8px',
        fontSize: '0.75rem',
        background: '#E6F3FF',
        color: 'var(--cgiar-blue)',
        borderRadius: '4px',
        fontWeight: 500,
      }}
    >
      <Info size={12} />
      {totalProcessed} updated
    </span>
  );
}
