'use client';

import { motion } from 'framer-motion';
import { Database, Search, Globe, RefreshCw, ThumbsUp, ThumbsDown } from 'lucide-react';
import { Partner } from '../types';
import { QualityBadge } from './QualityBadge';

interface PartnerRowProps {
  partner: Partner;
  index: number;
  runningWebSearch: { [key: string]: boolean };
  onViewClarisa: (partner: Partner) => void;
  onViewCandidates: (partner: Partner) => void;
  onViewWebSearch: (partner: Partner) => void;
  onRunWebSearch: (partner: Partner) => void;
  onAccept?: (partner: Partner) => void;
  onReject?: (partner: Partner) => void;
  respondingToRequest?: boolean;
}

export const PartnerRow = ({
  partner,
  index,
  runningWebSearch,
  onViewClarisa,
  onViewCandidates,
  onViewWebSearch,
  onRunWebSearch,
  onAccept,
  onReject,
  respondingToRequest,
}: PartnerRowProps) => {
  return (
    <motion.tr
      key={index}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: index * 0.02 }}
      style={{
        borderBottom: '1px solid var(--cgiar-gray)',
        transition: 'background 0.2s',
      }}
      onMouseOver={(e) => (e.currentTarget.style.background = '#FAFBFC')}
      onMouseOut={(e) => (e.currentTarget.style.background = 'white')}
    >
      <td
        style={{
          padding: 'var(--space-sm) var(--space-md)',
          color: 'var(--cgiar-navy)',
          fontWeight: 500,
        }}
      >
        <div>
          <div>{partner.name}</div>
          {partner.website && (
            <div
              style={{
                fontSize: '0.6875rem',
                color: 'var(--color-text-muted)',
                marginTop: '2px',
              }}
            >
              🌐 {partner.website}
            </div>
          )}
        </div>
      </td>
      <td
        style={{
          padding: 'var(--space-sm) var(--space-md)',
          color: 'var(--color-text-secondary)',
        }}
      >
        {partner.acronym && (
          <span
            style={{
              padding: '2px 8px',
              background: 'var(--cgiar-light-gray)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.6875rem',
              fontWeight: 500,
            }}
          >
            {partner.acronym}
          </span>
        )}
      </td>
      <td
        style={{
          padding: 'var(--space-sm) var(--space-md)',
          color: 'var(--color-text-secondary)',
        }}
      >
        {partner.country && <span>📍 {partner.country}</span>}
      </td>
      <td
        style={{
          padding: 'var(--space-sm) var(--space-md)',
          textAlign: 'center',
        }}
      >
        <QualityBadge quality={partner.match_quality} />
      </td>
      <td
        style={{
          padding: 'var(--space-sm) var(--space-md)',
          textAlign: 'center',
        }}
      >
        {partner.clarisa_match ? (
          <button
            onClick={() => onViewClarisa(partner)}
            style={{
              padding: '6px 12px',
              background: 'var(--cgiar-blue)',
              color: 'white',
              borderRadius: 'var(--radius-sm)',
              border: 'none',
              cursor: 'pointer',
              fontSize: '0.75rem',
              fontWeight: 500,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              transition: 'all 0.2s',
            }}
            onMouseOver={(e) => (e.currentTarget.style.opacity = '0.8')}
            onMouseOut={(e) => (e.currentTarget.style.opacity = '1')}
          >
            <Database size={14} />
            View
          </button>
        ) : (
          <span style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem' }}>—</span>
        )}
      </td>
      <td
        style={{
          padding: 'var(--space-sm) var(--space-md)',
          textAlign: 'center',
        }}
      >
        {partner.top_candidates && partner.top_candidates.length > 0 ? (
          <button
            onClick={() => onViewCandidates(partner)}
            style={{
              padding: '6px 12px',
              background: 'linear-gradient(135deg, #8B5CF6 0%, #6D28D9 100%)',
              color: 'white',
              borderRadius: 'var(--radius-sm)',
              border: 'none',
              cursor: 'pointer',
              fontSize: '0.75rem',
              fontWeight: 600,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              transition: 'all 0.2s',
              boxShadow: 'var(--shadow-sm)',
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = 'var(--shadow-md)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
            }}
          >
            <Search size={14} />
            View {partner.top_candidates.length}
          </button>
        ) : (
          <span style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem' }}>—</span>
        )}
      </td>
      <td
        style={{
          padding: 'var(--space-sm) var(--space-md)',
          textAlign: 'center',
        }}
      >
        {partner.web_search ? (
          <button
            onClick={() => onViewWebSearch(partner)}
            style={{
              padding: '6px 12px',
              background: 'var(--cgiar-yellow)',
              color: 'var(--cgiar-navy)',
              borderRadius: 'var(--radius-sm)',
              border: 'none',
              cursor: 'pointer',
              fontSize: '0.75rem',
              fontWeight: 500,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              transition: 'all 0.2s',
            }}
            onMouseOver={(e) => (e.currentTarget.style.opacity = '0.8')}
            onMouseOut={(e) => (e.currentTarget.style.opacity = '1')}
          >
            <Globe size={14} />
            View
          </button>
        ) : partner.match_quality === 'fair' || partner.match_quality === 'good' ? (
          <button
            onClick={() => onRunWebSearch(partner)}
            disabled={runningWebSearch[partner.id]}
            style={{
              padding: '6px 12px',
              background: runningWebSearch[partner.id]
                ? 'var(--cgiar-gray)'
                : 'rgba(252, 211, 77, 0.3)',
              color: runningWebSearch[partner.id] ? 'white' : 'var(--cgiar-navy)',
              borderRadius: 'var(--radius-sm)',
              border: runningWebSearch[partner.id]
                ? 'none'
                : '1px solid rgba(252, 211, 77, 0.6)',
              cursor: runningWebSearch[partner.id] ? 'not-allowed' : 'pointer',
              fontSize: '0.75rem',
              fontWeight: 500,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              transition: 'all 0.2s',
              opacity: runningWebSearch[partner.id] ? 0.7 : 1,
            }}
            onMouseOver={(e) =>
              !runningWebSearch[partner.id] &&
              (e.currentTarget.style.background = 'rgba(252, 211, 77, 0.5)')
            }
            onMouseOut={(e) =>
              !runningWebSearch[partner.id] &&
              (e.currentTarget.style.background = 'rgba(252, 211, 77, 0.3)')
            }
          >
            {runningWebSearch[partner.id] ? (
              <>
                <RefreshCw size={14} style={{ animation: 'spin 1s linear infinite' }} />
                Searching...
              </>
            ) : (
              <>
                <Globe size={14} />
                Run
              </>
            )}
          </button>
        ) : (
          <span style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem' }}>—</span>
        )}
      </td>
      <td
        style={{
          padding: 'var(--space-sm) var(--space-md)',
          textAlign: 'center',
        }}
      >
        {partner.api_data && onAccept && onReject ? (
          <div
            style={{
              display: 'flex',
              gap: '8px',
              justifyContent: 'center',
              alignItems: 'center',
            }}
          >
            <button
              onClick={() => onAccept(partner)}
              disabled={respondingToRequest}
              style={{
                padding: '6px 10px',
                background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                color: 'white',
                borderRadius: 'var(--radius-sm)',
                border: 'none',
                cursor: respondingToRequest ? 'not-allowed' : 'pointer',
                fontSize: '0.75rem',
                fontWeight: 600,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                transition: 'all 0.2s',
                boxShadow: 'var(--shadow-sm)',
                opacity: respondingToRequest ? 0.6 : 1,
              }}
              onMouseOver={(e) => {
                if (!respondingToRequest) {
                  e.currentTarget.style.transform = 'translateY(-2px)';
                  e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                }
              }}
              onMouseOut={(e) => {
                if (!respondingToRequest) {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                }
              }}
            >
              <ThumbsUp size={14} />
              Accept
            </button>
            <button
              onClick={() => onReject(partner)}
              disabled={respondingToRequest}
              style={{
                padding: '6px 10px',
                background: 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)',
                color: 'white',
                borderRadius: 'var(--radius-sm)',
                border: 'none',
                cursor: respondingToRequest ? 'not-allowed' : 'pointer',
                fontSize: '0.75rem',
                fontWeight: 600,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                transition: 'all 0.2s',
                boxShadow: 'var(--shadow-sm)',
                opacity: respondingToRequest ? 0.6 : 1,
              }}
              onMouseOver={(e) => {
                if (!respondingToRequest) {
                  e.currentTarget.style.transform = 'translateY(-2px)';
                  e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                }
              }}
              onMouseOut={(e) => {
                if (!respondingToRequest) {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                }
              }}
            >
              <ThumbsDown size={14} />
              Reject
            </button>
          </div>
        ) : (
          <span style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem' }}>—</span>
        )}
      </td>
    </motion.tr>
  );
};
