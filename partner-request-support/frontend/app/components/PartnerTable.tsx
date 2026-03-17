'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Info } from 'lucide-react';
import { Partner } from '../types';
import { PartnerRow } from './PartnerRow';

interface PartnerTableProps {
  partners: Partner[];
  runningWebSearch: { [key: string]: boolean };
  onViewClarisa: (partner: Partner) => void;
  onViewCandidates: (partner: Partner) => void;
  onViewWebSearch: (partner: Partner) => void;
  onRunWebSearch: (partner: Partner) => void;
  onAccept?: (partner: Partner) => void;
  onReject?: (partner: Partner) => void;
  respondingToRequest?: boolean;
}

export const PartnerTable = ({
  partners,
  runningWebSearch,
  onViewClarisa,
  onViewCandidates,
  onViewWebSearch,
  onRunWebSearch,
  onAccept,
  onReject,
  respondingToRequest,
}: PartnerTableProps) => {
  const [showQualityInfo, setShowQualityInfo] = useState(false);

  return (
    <div
      style={{
        background: 'white',
        borderRadius: 'var(--radius-md)',
        boxShadow: 'var(--shadow-sm)',
        overflow: 'hidden',
      }}
    >
      <div style={{ overflowX: 'auto' }}>
        <table
          style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: '0.8125rem',
          }}
        >
          <thead>
            <tr
              style={{
                background: 'var(--cgiar-light-gray)',
                borderBottom: '2px solid var(--cgiar-gray)',
              }}
            >
              <th
                style={{
                  padding: 'var(--space-sm) var(--space-md)',
                  textAlign: 'left',
                  fontWeight: 600,
                  color: 'var(--cgiar-navy)',
                  fontSize: '0.75rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                }}
              >
                Partner Name
              </th>
              <th
                style={{
                  padding: 'var(--space-sm) var(--space-md)',
                  textAlign: 'left',
                  fontWeight: 600,
                  color: 'var(--cgiar-navy)',
                  fontSize: '0.75rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                }}
              >
                Acronym
              </th>
              <th
                style={{
                  padding: 'var(--space-sm) var(--space-md)',
                  textAlign: 'left',
                  fontWeight: 600,
                  color: 'var(--cgiar-navy)',
                  fontSize: '0.75rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                }}
              >
                Country
              </th>
              <th
                style={{
                  padding: 'var(--space-sm) var(--space-md)',
                  textAlign: 'center',
                  fontWeight: 600,
                  color: 'var(--cgiar-navy)',
                  fontSize: '0.75rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  position: 'relative',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '4px',
                  }}
                >
                  Match Quality
                  <div
                    style={{ position: 'relative', display: 'inline-flex' }}
                    onMouseEnter={() => setShowQualityInfo(true)}
                    onMouseLeave={() => setShowQualityInfo(false)}
                  >
                    <Info
                      size={14}
                      style={{
                        cursor: 'help',
                        color: 'var(--cgiar-blue)',
                        transition: 'color 0.2s',
                      }}
                    />
                    <AnimatePresence>
                      {showQualityInfo && (
                        <motion.div
                          initial={{ opacity: 0, y: -5 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: -5 }}
                          transition={{ duration: 0.2 }}
                          style={{
                            position: 'absolute',
                            top: '24px',
                            left: '50%',
                            transform: 'translateX(-50%)',
                            background: 'white',
                            border: '1px solid var(--cgiar-gray)',
                            borderRadius: 'var(--radius-md)',
                            padding: 'var(--space-sm)',
                            boxShadow: 'var(--shadow-lg)',
                            zIndex: 1000,
                            width: '280px',
                            textAlign: 'left',
                            fontSize: '0.75rem',
                            fontWeight: 400,
                            textTransform: 'none',
                            letterSpacing: 'normal',
                            pointerEvents: 'none',
                          }}
                        >
                          <div
                            style={{
                              fontWeight: 600,
                              color: 'var(--cgiar-navy)',
                              marginBottom: '6px',
                              fontSize: '0.8125rem',
                            }}
                          >
                            Match Quality Levels
                          </div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <div
                                style={{
                                  width: '8px',
                                  height: '8px',
                                  borderRadius: '50%',
                                  background: 'var(--color-excellent)',
                                }}
                              />
                              <span style={{ color: 'var(--color-text-secondary)' }}>
                                <strong>Excellent</strong> (≥85%): High confidence match
                              </span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <div
                                style={{
                                  width: '8px',
                                  height: '8px',
                                  borderRadius: '50%',
                                  background: 'var(--color-good)',
                                }}
                              />
                              <span style={{ color: 'var(--color-text-secondary)' }}>
                                <strong>Good</strong> (≥70%): Strong match
                              </span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <div
                                style={{
                                  width: '8px',
                                  height: '8px',
                                  borderRadius: '50%',
                                  background: 'var(--color-fair)',
                                }}
                              />
                              <span style={{ color: 'var(--color-text-secondary)' }}>
                                <strong>Fair</strong> (≥60%): Moderate match
                              </span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <div
                                style={{
                                  width: '8px',
                                  height: '8px',
                                  borderRadius: '50%',
                                  background: 'var(--color-no-match)',
                                }}
                              />
                              <span style={{ color: 'var(--color-text-secondary)' }}>
                                <strong>No Match</strong> (&lt;60%): Below threshold
                              </span>
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </div>
              </th>
              <th
                style={{
                  padding: 'var(--space-sm) var(--space-md)',
                  textAlign: 'center',
                  fontWeight: 600,
                  color: 'var(--cgiar-navy)',
                  fontSize: '0.75rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                }}
              >
                CLARISA
              </th>
              <th
                style={{
                  padding: 'var(--space-sm) var(--space-md)',
                  textAlign: 'center',
                  fontWeight: 600,
                  color: 'var(--cgiar-navy)',
                  fontSize: '0.75rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                }}
              >
                Top Candidates
              </th>
              <th
                style={{
                  padding: 'var(--space-sm) var(--space-md)',
                  textAlign: 'center',
                  fontWeight: 600,
                  color: 'var(--cgiar-navy)',
                  fontSize: '0.75rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                }}
              >
                Web Search
              </th>
              <th
                style={{
                  padding: 'var(--space-sm) var(--space-md)',
                  textAlign: 'center',
                  fontWeight: 600,
                  color: 'var(--cgiar-navy)',
                  fontSize: '0.75rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                }}
              >
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {partners.map((partner, index) => (
              <PartnerRow
                key={partner.id}
                partner={partner}
                index={index}
                runningWebSearch={runningWebSearch}
                onViewClarisa={onViewClarisa}
                onViewCandidates={onViewCandidates}
                onViewWebSearch={onViewWebSearch}
                onRunWebSearch={onRunWebSearch}
                onAccept={onAccept}
                onReject={onReject}
                respondingToRequest={respondingToRequest}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
