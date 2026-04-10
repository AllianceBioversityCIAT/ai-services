'use client';

import { motion } from 'framer-motion';
import { FileSpreadsheet, XCircle } from 'lucide-react';
import { AuthUser } from '../types/auth.types';

interface HeaderProps {
  authUser: AuthUser | null;
  onLogout: () => void;
}

export const Header = ({ authUser, onLogout }: HeaderProps) => {
  return (
    <header
      style={{
        background: 'white',
        borderBottom: '1px solid var(--cgiar-gray)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      <div
        style={{
          maxWidth: '1400px',
          margin: '0 auto',
          padding: 'var(--space-sm) var(--space-lg)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}
        >
          <div
            style={{
              width: '40px',
              height: '40px',
              background: 'var(--cgiar-green)',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <FileSpreadsheet size={24} color="white" />
          </div>
          <div>
            <h1
              style={{
                fontSize: '1.25rem',
                fontWeight: 600,
                color: 'var(--cgiar-navy)',
                marginBottom: '2px',
              }}
            >
              Partner Request Support
            </h1>
            <p
              style={{
                fontSize: '0.75rem',
                color: 'var(--color-text-muted)',
                fontWeight: 400,
              }}
            >
              CGIAR Institutional Mapping
            </p>
          </div>
        </motion.div>

        {/* Production Environment Tag */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          style={{
            background: '#81c003',
            color: 'white',
            padding: '8px 20px',
            borderRadius: 'var(--radius-md)',
            fontSize: '0.875rem',
            fontWeight: 600,
            boxShadow: '0 2px 8px rgba(220, 38, 38, 0.25)',
            letterSpacing: '0.5px',
          }}
        >
          Production Environment
        </motion.div>

        {/* User info and logout */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-md)',
          }}
        >
          <div
            style={{
              textAlign: 'right',
              marginRight: 'var(--space-sm)',
            }}
          >
            <p
              style={{
                fontSize: '0.875rem',
                fontWeight: 600,
                color: 'var(--cgiar-navy)',
                marginBottom: '2px',
              }}
            >
              {authUser?.name || authUser?.username}
            </p>
            <p
              style={{
                fontSize: '0.75rem',
                color: 'var(--color-text-muted)',
              }}
            >
              {authUser?.email}
            </p>
          </div>
          <button
            onClick={onLogout}
            style={{
              padding: '8px 16px',
              background: 'white',
              color: 'var(--cgiar-navy)',
              border: '2px solid var(--cgiar-gray)',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.875rem',
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'all 0.2s',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.borderColor = 'var(--color-error)';
              e.currentTarget.style.color = 'var(--color-error)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.borderColor = 'var(--cgiar-gray)';
              e.currentTarget.style.color = 'var(--cgiar-navy)';
            }}
          >
            <XCircle size={16} />
            Logout
          </button>
        </motion.div>
      </div>
    </header>
  );
};
