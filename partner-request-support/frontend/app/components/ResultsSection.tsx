'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Search } from 'lucide-react';
import { ProcessingResults, Partner, SyncInfo } from '../types';
import { filterPartners } from '../utils/fileHelpers';
import { StatsCards } from './StatsCards';
import { SyncAlert } from './SyncAlert';
import { PartnerTable } from './PartnerTable';

interface ResultsSectionProps {
  results: ProcessingResults;
  runningWebSearch: { [key: string]: boolean };
  onViewClarisa: (partner: Partner) => void;
  onViewCandidates: (partner: Partner) => void;
  onViewWebSearch: (partner: Partner) => void;
  onRunWebSearch: (partner: Partner) => void;
  onAccept?: (partner: Partner) => void;
  onReject?: (partner: Partner) => void;
  respondingToRequest?: boolean;
  onNewUpload: () => void;
}

export const ResultsSection = ({
  results,
  runningWebSearch,
  onViewClarisa,
  onViewCandidates,
  onViewWebSearch,
  onRunWebSearch,
  onAccept,
  onReject,
  respondingToRequest,
  onNewUpload,
}: ResultsSectionProps) => {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredPartners = filterPartners(results.partners, searchQuery);

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
      {/* Sync Info Alert */}
      {results.sync_info && <SyncAlert syncInfo={results.sync_info} className="mb-4" />}

      {/* Statistics Grid */}
      <StatsCards stats={results.stats} />

      {/* Results Header */}
      <div
        style={{
          background: '#F0F7FC',
          padding: 'var(--space-md)',
          borderRadius: 'var(--radius-md)',
          marginBottom: 'var(--space-sm)',
          boxShadow: 'var(--shadow-sm)',
          border: '1px solid #D4E7F4',
          borderLeft: '4px solid var(--cgiar-blue)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 'var(--space-sm)',
        }}
      >
        <div>
          <h2
            style={{
              fontSize: '1.25rem',
              fontWeight: 600,
              color: 'var(--cgiar-navy)',
              marginBottom: '2px',
            }}
          >
            Partner Results
          </h2>
          <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
            {filteredPartners.length} partners {searchQuery && `matching "${searchQuery}"`}
          </p>
        </div>

        <div style={{ display: 'flex', gap: 'var(--space-sm)', alignItems: 'center' }}>
          {/* Search */}
          <div style={{ position: 'relative' }}>
            <Search
              size={16}
              style={{
                position: 'absolute',
                left: '10px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--color-text-muted)',
              }}
            />
            <input
              type="text"
              placeholder="Search partners..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                padding: '8px 14px 8px 36px',
                border: '1px solid var(--cgiar-gray)',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.8125rem',
                width: '220px',
                outline: 'none',
                fontFamily: 'var(--font-primary)',
                background: 'white',
              }}
            />
          </div>

          {/* New Upload Button */}
          <button
            onClick={onNewUpload}
            style={{
              padding: '8px 16px',
              background: 'var(--cgiar-green)',
              color: 'white',
              borderRadius: 'var(--radius-md)',
              fontWeight: 500,
              fontSize: '0.8125rem',
              transition: 'all 0.2s',
              boxShadow: 'var(--shadow-sm)',
              border: 'none',
              cursor: 'pointer',
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.background = 'var(--color-primary-dark)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.background = 'var(--cgiar-green)';
            }}
          >
            New Upload
          </button>
        </div>
      </div>

      {/* Partners Table */}
      <PartnerTable
        partners={filteredPartners}
        runningWebSearch={runningWebSearch}
        onViewClarisa={onViewClarisa}
        onViewCandidates={onViewCandidates}
        onViewWebSearch={onViewWebSearch}
        onRunWebSearch={onRunWebSearch}
        onAccept={onAccept}
        onReject={onReject}
        respondingToRequest={respondingToRequest}
      />
    </motion.div>
  );
};
