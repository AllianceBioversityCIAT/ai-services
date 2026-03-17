'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { CheckCircle2, ThumbsUp, ThumbsDown, AlertCircle } from 'lucide-react';
import { Partner, ModalType } from '../types';

interface ModalProps {
  isOpen: boolean;
  type: ModalType | null;
  partner: Partner | null;
  onClose: () => void;
  onAccept?: () => void;
  onReject?: (value: string) => void;
  onConfirmReject?: () => void;
  rejectJustification?: string;
  responseMessage?: { type: 'success' | 'error', message: string } | null;
  isResponding?: boolean;
}

const DataField = ({ label, value, fullWidth }: { label: string; value: string; fullWidth?: boolean }) => (
  <div style={{ gridColumn: fullWidth ? '1 / -1' : 'auto' }}>
    <p style={{
      fontSize: '0.6875rem',
      color: 'var(--color-text-muted)',
      marginBottom: '2px',
      textTransform: 'uppercase',
      letterSpacing: '0.5px',
      fontWeight: 500,
    }}>
      {label}
    </p>
    <p style={{
      color: 'var(--cgiar-navy)',
      fontSize: '0.8125rem',
      fontWeight: 500,
    }}>
      {value}
    </p>
  </div>
);

const ScoreBar = ({ label, value }: { label: string; value: number }) => {
  const percentage = Math.round(value * 100);
  return (
    <div>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        marginBottom: '4px',
      }}>
        <span style={{
          fontSize: '0.6875rem',
          color: 'var(--color-text-secondary)',
          fontWeight: 500,
        }}>
          {label}
        </span>
        <span style={{
          fontSize: '0.6875rem',
          fontWeight: 700,
          color: 'var(--cgiar-green)',
        }}>
          {percentage}%
        </span>
      </div>
      <div style={{
        width: '100%',
        height: '6px',
        background: '#E0E5EB',
        borderRadius: '3px',
        overflow: 'hidden',
      }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 1, ease: 'easeOut' }}
          style={{
            height: '100%',
            background: 'linear-gradient(90deg, var(--cgiar-green) 0%, #629600 100%)',
            borderRadius: '4px',
          }}
        />
      </div>
    </div>
  );
};

export const Modal = ({ 
  isOpen, 
  type, 
  partner, 
  onClose, 
  onAccept, 
  onReject,
  onConfirmReject, 
  rejectJustification = '',
  responseMessage = null,
  isResponding 
}: ModalProps) => {
  if (!partner) return null;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(0, 0, 0, 0.5)',
              zIndex: 1000,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 'var(--space-lg)',
            }}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              style={{
                background: 'white',
                borderRadius: 'var(--radius-lg)',
                maxWidth: '1100px',
                width: '100%',
                maxHeight: '80vh',
                overflow: 'auto',
                boxShadow: 'var(--shadow-xl)',
              }}
            >
              {/* Modal Header */}
              <div style={{
                padding: 'var(--space-lg)',
                borderBottom: '1px solid var(--cgiar-gray)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'start',
                background: type === 'clarisa' ? 'var(--cgiar-blue)' : type === 'candidates' ? 'linear-gradient(135deg, #8B5CF6 0%, #6D28D9 100%)' : type === 'accept' ? 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)' : type === 'reject' ? 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)' : 'var(--cgiar-yellow)',
                borderTopLeftRadius: 'var(--radius-lg)',
                borderTopRightRadius: 'var(--radius-lg)',
              }}>
                <div>
                  <h3 style={{
                    color: type === 'candidates' || type === 'clarisa' || type === 'accept' || type === 'reject' ? 'white' : 'var(--cgiar-navy)',
                    fontSize: '1.125rem',
                    fontWeight: 600,
                    marginBottom: '4px',
                  }}>
                    {partner.name}
                  </h3>
                  <p style={{
                    color: type === 'candidates' || type === 'clarisa' || type === 'accept' || type === 'reject' ? 'rgba(255,255,255,0.9)' : 'var(--color-text-secondary)',
                    fontSize: '0.875rem',
                  }}>
                    {type === 'clarisa' ? 'CLARISA Match Details' : type === 'candidates' ? 'Top Candidate Matches' : type === 'accept' ? 'Accept Partner Request' : type === 'reject' ? 'Reject Partner Request' : 'Web Search Results'}
                  </p>
                </div>
                <button
                  onClick={onClose}
                  style={{
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: type === 'candidates' || type === 'clarisa' || type === 'accept' || type === 'reject' ? 'white' : 'var(--cgiar-navy)',
                    fontSize: '1.5rem',
                    lineHeight: 1,
                    padding: '4px',
                  }}
                >
                  ×
                </button>
              </div>

              {/* Modal Body */}
              <div style={{ padding: 'var(--space-lg)' }}>
                {/* CLARISA Match */}
                {type === 'clarisa' && partner.clarisa_match && (
                  <div>
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                      gap: 'var(--space-md)',
                      marginBottom: 'var(--space-lg)',
                    }}>
                      <DataField label="Institution" value={partner.clarisa_match.name} />
                      <DataField label="CLARISA ID" value={partner.clarisa_match.clarisa_id} />
                      {partner.clarisa_match.acronym && (
                        <DataField label="Acronym" value={partner.clarisa_match.acronym} />
                      )}
                      {partner.clarisa_match.institution_type && (
                        <DataField label="Type" value={partner.clarisa_match.institution_type} />
                      )}
                      {partner.clarisa_match.countries.length > 0 && (
                        <DataField
                          label="Countries"
                          value={partner.clarisa_match.countries.join(', ')}
                          fullWidth
                        />
                      )}
                      {partner.clarisa_match.website && (
                        <DataField
                          label="Website"
                          value={partner.clarisa_match.website}
                          fullWidth
                        />
                      )}
                    </div>

                    <div style={{
                      background: 'var(--cgiar-light-gray)',
                      padding: 'var(--space-md)',
                      borderRadius: 'var(--radius-md)',
                    }}>
                      <p style={{
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        color: 'var(--color-text-secondary)',
                        marginBottom: 'var(--space-sm)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                      }}>
                        Match Confidence Scores
                      </p>
                      <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                        gap: 'var(--space-sm)',
                      }}>
                        <ScoreBar
                          label="Final Score"
                          value={partner.clarisa_match.scores.final_score}
                        />
                        <ScoreBar
                          label="Similarity"
                          value={partner.clarisa_match.scores.cosine_similarity}
                        />
                        <ScoreBar
                          label="Name Match"
                          value={partner.clarisa_match.scores.fuzz_name_score}
                        />
                        <ScoreBar
                          label="Acronym Match"
                          value={partner.clarisa_match.scores.fuzz_acronym_score}
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* Web Search */}
                {type === 'websearch' && partner.web_search && (
                  <div>
                    {partner.web_search.success ? (
                      <div className="markdown-content" style={{
                        background: '#FAFBFC',
                        padding: 'var(--space-md)',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: '0.8125rem',
                        lineHeight: 1.5,
                        color: 'var(--color-text-secondary)',
                        fontFamily: 'var(--font-primary)',
                      }}>
                        <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
                          {partner.web_search.result || ''}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <div style={{
                        padding: 'var(--space-md)',
                        background: '#FEE',
                        border: '1px solid var(--color-error)',
                        borderRadius: 'var(--radius-sm)',
                        color: 'var(--color-error)',
                        fontSize: '0.875rem',
                      }}>
                        ⚠️ {partner.web_search.error}
                      </div>
                    )}
                  </div>
                )}

                {/* Top Candidates */}
                {type === 'candidates' && partner.top_candidates && (
                  <div>
                    <div style={{
                      marginBottom: 'var(--space-md)',
                      padding: 'var(--space-sm) var(--space-md)',
                      background: 'linear-gradient(135deg, #F3E8FF 0%, #EDE9FE 100%)',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid #C4B5FD',
                      borderLeft: '4px solid #8B5CF6',
                    }}>
                      <p style={{
                        fontSize: '0.8125rem',
                        color: 'var(--cgiar-navy)',
                        lineHeight: 1.5,
                        margin: 0,
                      }}>
                        <strong>ℹ️ Information:</strong> These are the top {partner.top_candidates.length} candidate matches from the CLARISA database, ranked by relevance score. {partner.match_found ? 'The first candidate exceeded the match threshold and was selected as the primary match.' : 'None of these candidates exceeded the match threshold, but they represent the closest matches found.'}
                      </p>
                    </div>

                    <div style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 'var(--space-md)',
                    }}>
                      {partner.top_candidates.map((candidate, idx) => (
                        <motion.div
                          key={idx}
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: idx * 0.05 }}
                          style={{
                            background: 'white',
                            border: idx === 0 && partner.match_found ? '2px solid var(--cgiar-green)' : '1px solid var(--cgiar-gray)',
                            borderRadius: 'var(--radius-md)',
                            padding: 'var(--space-md)',
                            position: 'relative',
                            boxShadow: 'var(--shadow-sm)',
                          }}
                        >
                          {/* Rank Badge */}
                          <div style={{
                            position: 'absolute',
                            top: '-12px',
                            left: 'var(--space-md)',
                            background: idx === 0 && partner.match_found ? 'var(--cgiar-green)' : 'linear-gradient(135deg, #8B5CF6 0%, #6D28D9 100%)',
                            color: 'white',
                            padding: '4px 12px',
                            borderRadius: 'var(--radius-md)',
                            fontSize: '0.6875rem',
                            fontWeight: 700,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            boxShadow: 'var(--shadow-sm)',
                          }}>
                            {idx === 0 && partner.match_found && <CheckCircle2 size={12} />}
                            #{idx + 1} {idx === 0 && partner.match_found && 'SELECTED'}
                          </div>

                          {/* Candidate Info */}
                          <div style={{ marginTop: 'var(--space-xs)' }}>
                            <h4 style={{
                              fontSize: '1rem',
                              fontWeight: 600,
                              color: 'var(--cgiar-navy)',
                              marginBottom: 'var(--space-xs)',
                            }}>
                              {candidate.name}
                            </h4>
                            
                            <div style={{
                              display: 'grid',
                              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                              gap: 'var(--space-sm)',
                              marginBottom: 'var(--space-sm)',
                            }}>
                              {candidate.clarisa_id && (
                                <div style={{ fontSize: '0.75rem' }}>
                                  <span style={{ color: 'var(--color-text-muted)', fontWeight: 500 }}>ID: </span>
                                  <span style={{ color: 'var(--cgiar-navy)', fontWeight: 600 }}>{candidate.clarisa_id}</span>
                                </div>
                              )}
                              {candidate.acronym && (
                                <div style={{ fontSize: '0.75rem' }}>
                                  <span style={{ color: 'var(--color-text-muted)', fontWeight: 500 }}>Acronym: </span>
                                  <span style={{
                                    padding: '2px 6px',
                                    background: 'var(--cgiar-light-gray)',
                                    borderRadius: 'var(--radius-sm)',
                                    fontWeight: 600,
                                    color: 'var(--cgiar-navy)',
                                  }}>{candidate.acronym}</span>
                                </div>
                              )}
                              {candidate.institution_type && (
                                <div style={{ fontSize: '0.75rem' }}>
                                  <span style={{ color: 'var(--color-text-muted)', fontWeight: 500 }}>Type: </span>
                                  <span style={{ color: 'var(--color-text-secondary)' }}>{candidate.institution_type}</span>
                                </div>
                              )}
                            </div>

                            {candidate.countries.length > 0 && (
                              <div style={{
                                fontSize: '0.75rem',
                                marginBottom: 'var(--space-xs)',
                              }}>
                                <span style={{ color: 'var(--color-text-muted)', fontWeight: 500 }}>Countries: </span>
                                <span style={{ color: 'var(--color-text-secondary)' }}>{candidate.countries.join(', ')}</span>
                              </div>
                            )}

                            {candidate.website && (
                              <div style={{
                                fontSize: '0.75rem',
                                marginBottom: 'var(--space-sm)',
                              }}>
                                <span style={{ color: 'var(--color-text-muted)', fontWeight: 500 }}>Website: </span>
                                <a
                                  href={candidate.website.startsWith('http') ? candidate.website : `https://${candidate.website}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  style={{
                                    color: 'var(--cgiar-blue)',
                                    textDecoration: 'none',
                                    fontWeight: 500,
                                  }}
                                >
                                  {candidate.website}
                                </a>
                              </div>
                            )}

                            {/* Score Bars */}
                            <div style={{
                              background: 'var(--cgiar-light-gray)',
                              padding: 'var(--space-sm)',
                              borderRadius: 'var(--radius-sm)',
                              marginTop: 'var(--space-sm)',
                            }}>
                              <p style={{
                                fontSize: '0.6875rem',
                                fontWeight: 600,
                                color: 'var(--color-text-secondary)',
                                marginBottom: 'var(--space-xs)',
                                textTransform: 'uppercase',
                                letterSpacing: '0.5px',
                              }}>
                                Match Scores
                              </p>
                              <div style={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
                                gap: 'var(--space-xs)',
                              }}>
                                <ScoreBar
                                  label="Final"
                                  value={candidate.scores.final_score}
                                />
                                <ScoreBar
                                  label="Similarity"
                                  value={candidate.scores.cosine_similarity}
                                />
                                <ScoreBar
                                  label="Name"
                                  value={candidate.scores.fuzz_name_score}
                                />
                                <ScoreBar
                                  label="Acronym"
                                  value={candidate.scores.fuzz_acronym_score}
                                />
                              </div>
                            </div>
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Accept Confirmation Modal */}
                {type === 'accept' && partner && (
                  <div style={{
                    padding: 'var(--space-md)',
                  }}>
                    {responseMessage ? (
                      <div style={{
                        padding: 'var(--space-md)',
                        background: responseMessage.type === 'success' ? '#D1FAE5' : '#FEE2E2',
                        border: `1px solid ${responseMessage.type === 'success' ? '#10B981' : '#EF4444'}`,
                        borderRadius: 'var(--radius-sm)',
                        color: responseMessage.type === 'success' ? '#065F46' : '#991B1B',
                        fontSize: '0.875rem',
                        marginBottom: 'var(--space-md)',
                      }}>
                        {responseMessage.type === 'success' ? '✓' : '⚠️'} {responseMessage.message}
                      </div>
                    ) : (
                      <>
                        <div style={{
                          marginBottom: 'var(--space-lg)',
                          textAlign: 'center',
                        }}>
                          <div style={{
                            width: '48px',
                            height: '48px',
                            borderRadius: '50%',
                            background: 'linear-gradient(135deg, #D1FAE5 0%, #A7F3D0 100%)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            margin: '0 auto var(--space-md)',
                          }}>
                            <ThumbsUp size={24} style={{ color: '#059669' }} />
                          </div>
                          <h3 style={{
                            fontSize: '1rem',
                            fontWeight: 600,
                            color: 'var(--cgiar-navy)',
                            marginBottom: 'var(--space-xs)',
                          }}>
                            Accept Partner Request
                          </h3>
                          <p style={{
                            fontSize: '0.8125rem',
                            color: 'var(--color-text-secondary)',
                            lineHeight: 1.5,
                          }}>
                            This action will notify the partner and create a record in the CLARISA system.
                          </p>
                        </div>

                        <div style={{
                          display: 'flex',
                          gap: 'var(--space-sm)',
                          justifyContent: 'center',
                        }}>
                          <button
                            onClick={onClose}
                            disabled={isResponding}
                            style={{
                              padding: '10px 20px',
                              background: 'white',
                              color: 'var(--cgiar-navy)',
                              border: '2px solid var(--cgiar-gray)',
                              borderRadius: 'var(--radius-md)',
                              cursor: isResponding ? 'not-allowed' : 'pointer',
                              fontSize: '0.875rem',
                              fontWeight: 500,
                              transition: 'all 0.2s',
                              opacity: isResponding ? 0.5 : 1,
                            }}
                            onMouseOver={(e) => !isResponding && (e.currentTarget.style.borderColor = 'var(--color-text-muted)')}
                            onMouseOut={(e) => !isResponding && (e.currentTarget.style.borderColor = 'var(--cgiar-gray)')}
                          >
                            Cancel
                          </button>
                          <button
                            onClick={onAccept}
                            disabled={isResponding}
                            style={{
                              padding: '10px 20px',
                              background: isResponding ? 'var(--cgiar-gray)' : 'var(--cgiar-green)',
                              color: 'white',
                              border: 'none',
                              borderRadius: 'var(--radius-md)',
                              cursor: isResponding ? 'not-allowed' : 'pointer',
                              fontSize: '0.875rem',
                              fontWeight: 600,
                              transition: 'all 0.2s',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '6px',
                            }}
                            onMouseOver={(e) => {
                              if (!isResponding) {
                                e.currentTarget.style.background = '#059669';
                                e.currentTarget.style.transform = 'translateY(-1px)';
                                e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                              }
                            }}
                            onMouseOut={(e) => {
                              if (!isResponding) {
                                e.currentTarget.style.background = 'var(--cgiar-green)';
                                e.currentTarget.style.transform = 'translateY(0)';
                                e.currentTarget.style.boxShadow = 'none';
                              }
                            }}
                          >
                            {isResponding ? (
                              <>Processing...</>
                            ) : (
                              <>
                                <ThumbsUp size={16} />
                                Yes, Accept
                              </>
                            )}
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                )}

                {/* Reject Modal with Justification */}
                {type === 'reject' && partner && (
                  <div style={{
                    padding: 'var(--space-md)',
                  }}>
                    {responseMessage ? (
                      <div style={{
                        padding: 'var(--space-md)',
                        background: responseMessage.type === 'success' ? '#D1FAE5' : '#FEE2E2',
                        border: `1px solid ${responseMessage.type === 'success' ? '#10B981' : '#EF4444'}`,
                        borderRadius: 'var(--radius-sm)',
                        color: responseMessage.type === 'success' ? '#065F46' : '#991B1B',
                        fontSize: '0.875rem',
                        marginBottom: 'var(--space-md)',
                      }}>
                        {responseMessage.type === 'success' ? '✓' : '⚠️'} {responseMessage.message}
                      </div>
                    ) : (
                      <>
                        <div style={{
                          marginBottom: 'var(--space-lg)',
                          padding: 'var(--space-md)',
                          background: 'linear-gradient(135deg, #FEE2E2 0%, #FECACA 100%)',
                          borderRadius: 'var(--radius-md)',
                          border: '1px solid #FCA5A5',
                          borderLeft: '4px solid #EF4444',
                        }}>
                          <div style={{
                            display: 'flex',
                            alignItems: 'start',
                            gap: 'var(--space-sm)',
                          }}>
                            <AlertCircle size={20} style={{ color: '#DC2626', flexShrink: 0, marginTop: '2px' }} />
                            <div>
                              <p style={{
                                fontSize: '0.875rem',
                                color: '#991B1B',
                                lineHeight: 1.5,
                                margin: 0,
                                fontWeight: 500,
                              }}>
                                You are about to reject this partner request
                              </p>
                              <p style={{
                                fontSize: '0.75rem',
                                color: '#7F1D1D',
                                marginTop: 'var(--space-xs)',
                                marginBottom: 0,
                              }}>
                                Please provide a reason below (optional) to help improve future submissions.
                              </p>
                            </div>
                          </div>
                        </div>

                        <div style={{ marginBottom: 'var(--space-lg)' }}>
                          <label style={{
                            display: 'block',
                            fontSize: '0.875rem',
                            fontWeight: 500,
                            color: 'var(--cgiar-navy)',
                            marginBottom: 'var(--space-xs)',
                          }}>
                            Rejection Reason (Optional)
                          </label>
                          <textarea
                            value={rejectJustification}
                            onChange={(e) => onReject && onReject(e.target.value)}
                            placeholder="Provide any details about why this request is being rejected..."
                            disabled={isResponding}
                            style={{
                              width: '100%',
                              minHeight: '120px',
                              padding: 'var(--space-sm)',
                              border: '1px solid var(--cgiar-gray)',
                              borderRadius: 'var(--radius-sm)',
                              fontSize: '0.875rem',
                              fontFamily: 'inherit',
                              resize: 'vertical',
                              background: isResponding ? '#F3F4F6' : 'white',
                            }}
                          />
                          <p style={{
                            fontSize: '0.75rem',
                            color: 'var(--color-text-muted)',
                            marginTop: 'var(--space-xs)',
                            marginBottom: 0,
                          }}>
                            {rejectJustification.length} characters
                          </p>
                        </div>

                        <div style={{
                          display: 'flex',
                          gap: 'var(--space-sm)',
                          justifyContent: 'flex-end',
                        }}>
                          <button
                            onClick={() => {
                              onClose();
                              onReject && onReject('');
                            }}
                            disabled={isResponding}
                            style={{
                              padding: '10px 20px',
                              background: 'white',
                              color: 'var(--cgiar-navy)',
                              border: '1px solid var(--cgiar-gray)',
                              borderRadius: 'var(--radius-sm)',
                              cursor: isResponding ? 'not-allowed' : 'pointer',
                              fontSize: '0.875rem',
                              fontWeight: 500,
                              transition: 'all 0.2s',
                              opacity: isResponding ? 0.5 : 1,
                            }}
                          >
                            Cancel
                          </button>
                          <button
                            onClick={onConfirmReject}
                            disabled={isResponding}
                            style={{
                              padding: '10px 20px',
                              background: 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)',
                              color: 'white',
                              border: 'none',
                              borderRadius: 'var(--radius-sm)',
                              cursor: isResponding ? 'not-allowed' : 'pointer',
                              fontSize: '0.875rem',
                              fontWeight: 600,
                              transition: 'all 0.2s',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '6px',
                              opacity: isResponding ? 0.5 : 1,
                            }}
                          >
                            {isResponding ? (
                              <>Processing...</>
                            ) : (
                              <>
                                <ThumbsDown size={16} />
                                Confirm Reject
                              </>
                            )}
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};
