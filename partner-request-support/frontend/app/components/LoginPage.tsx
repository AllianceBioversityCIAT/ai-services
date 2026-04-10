'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { FileSpreadsheet, CheckCircle2, Database, Globe, AlertCircle, Eye, EyeOff } from 'lucide-react';

interface LoginPageProps {
  onLogin: (email: string, password: string) => Promise<boolean>;
  loginError: string | null;
  isLoading: boolean;
}

export const LoginPage = ({ onLogin, loginError, isLoading }: LoginPageProps) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onLogin(email, password);
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--color-background)',
        display: 'flex',
      }}
    >
      {/* Left Side - Branding */}
      <div
        style={{
          flex: '1',
          background: 'linear-gradient(135deg, var(--cgiar-navy) 0%, #1a4d2e 100%)',
          padding: 'var(--space-2xl)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Decorative circles */}
        <div
          style={{
            position: 'absolute',
            width: '400px',
            height: '400px',
            borderRadius: '50%',
            background: 'rgba(16, 185, 129, 0.1)',
            top: '-200px',
            left: '-200px',
          }}
        />
        <div
          style={{
            position: 'absolute',
            width: '300px',
            height: '300px',
            borderRadius: '50%',
            background: 'rgba(16, 185, 129, 0.15)',
            bottom: '-150px',
            right: '-150px',
          }}
        />

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          style={{
            zIndex: 1,
            textAlign: 'center',
            maxWidth: '500px',
          }}
        >
          <div
            style={{
              width: '120px',
              height: '120px',
              background: 'rgba(255, 255, 255, 0.1)',
              backdropFilter: 'blur(10px)',
              borderRadius: 'var(--radius-xl)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto var(--space-xl)',
              border: '2px solid rgba(255, 255, 255, 0.2)',
            }}
          >
            <FileSpreadsheet size={60} color="white" />
          </div>

          <h1
            style={{
              fontSize: '2.5rem',
              fontWeight: 700,
              color: 'white',
              marginBottom: 'var(--space-md)',
              lineHeight: 1.2,
            }}
          >
            Partner Request Support
          </h1>
          <p
            style={{
              fontSize: '1.125rem',
              color: 'rgba(255, 255, 255, 0.8)',
              lineHeight: 1.6,
            }}
          >
            Streamline institutional matching and partner request management with AI-powered analysis
          </p>

          {/* Features */}
          <div
            style={{
              marginTop: 'var(--space-2xl)',
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-md)',
              textAlign: 'left',
            }}
          >
            {[
              { icon: CheckCircle2, text: 'AI-powered institution matching' },
              { icon: Database, text: 'CLARISA database integration' },
              { icon: Globe, text: 'Automated web research' },
            ].map((feature, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + idx * 0.1 }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-sm)',
                  color: 'rgba(255, 255, 255, 0.9)',
                }}
              >
                <feature.icon size={20} />
                <span style={{ fontSize: '0.9375rem' }}>{feature.text}</span>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Right Side - Login Form */}
      <div
        style={{
          flex: '1',
          padding: 'var(--space-2xl)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'white',
        }}
      >
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
          style={{
            width: '100%',
            maxWidth: '480px',
          }}
        >
          <div style={{ marginBottom: 'var(--space-2xl)' }}>
            <h2
              style={{
                fontSize: '1.875rem',
                fontWeight: 700,
                color: 'var(--cgiar-navy)',
                marginBottom: 'var(--space-xs)',
              }}
            >
              Welcome back
            </h2>
            <p
              style={{
                fontSize: '0.9375rem',
                color: 'var(--color-text-muted)',
              }}
            >
              Sign in to your account to continue
            </p>
          </div>

          {/* Login Form */}
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 'var(--space-lg)' }}>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  color: 'var(--cgiar-navy)',
                  marginBottom: 'var(--space-xs)',
                }}
              >
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your.email@cgiar.org"
                required
                disabled={isLoading}
                style={{
                  width: '100%',
                  padding: '14px var(--space-md)',
                  border: '1px solid var(--cgiar-gray)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '0.9375rem',
                  fontFamily: 'inherit',
                  transition: 'all 0.2s',
                  background: isLoading ? 'var(--cgiar-light-gray)' : 'white',
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = 'var(--cgiar-green)';
                  e.target.style.boxShadow = '0 0 0 3px rgba(16, 185, 129, 0.1)';
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = 'var(--cgiar-gray)';
                  e.target.style.boxShadow = 'none';
                }}
              />
            </div>

            <div style={{ marginBottom: 'var(--space-xl)' }}>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  color: 'var(--cgiar-navy)',
                  marginBottom: 'var(--space-xs)',
                }}
              >
                Password
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                  disabled={isLoading}
                  style={{
                    width: '100%',
                    padding: '14px var(--space-md)',
                    paddingRight: '48px',
                    border: '1px solid var(--cgiar-gray)',
                    borderRadius: 'var(--radius-md)',
                    fontSize: '0.9375rem',
                    fontFamily: 'inherit',
                    transition: 'all 0.2s',
                    background: isLoading ? 'var(--cgiar-light-gray)' : 'white',
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = 'var(--cgiar-green)';
                    e.target.style.boxShadow = '0 0 0 3px rgba(16, 185, 129, 0.1)';
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = 'var(--cgiar-gray)';
                    e.target.style.boxShadow = 'none';
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  disabled={isLoading}
                  style={{
                    position: 'absolute',
                    right: '12px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    cursor: isLoading ? 'not-allowed' : 'pointer',
                    padding: '4px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--color-text-muted)',
                    transition: 'color 0.2s',
                    opacity: isLoading ? 0.5 : 1,
                  }}
                  onMouseOver={(e) => !isLoading && (e.currentTarget.style.color = 'var(--cgiar-navy)')}
                  onMouseOut={(e) => !isLoading && (e.currentTarget.style.color = 'var(--color-text-muted)')}
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            {/* Error Message */}
            {loginError && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                style={{
                  marginBottom: 'var(--space-lg)',
                  padding: 'var(--space-md)',
                  background: '#FEF2F2',
                  border: '1px solid #FCA5A5',
                  borderRadius: 'var(--radius-md)',
                  color: '#991B1B',
                  fontSize: '0.875rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-xs)',
                }}
              >
                <AlertCircle size={18} />
                {loginError}
              </motion.div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading || !email || !password}
              style={{
                width: '100%',
                padding: '14px var(--space-lg)',
                background:
                  isLoading || !email || !password ? 'var(--cgiar-gray)' : 'var(--cgiar-green)',
                color: 'white',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                fontSize: '1rem',
                fontWeight: 600,
                cursor: isLoading || !email || !password ? 'not-allowed' : 'pointer',
                transition: 'all 0.2s',
              }}
              onMouseOver={(e) => {
                if (!isLoading && email && password) {
                  e.currentTarget.style.background = '#059669';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                  e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                }
              }}
              onMouseOut={(e) => {
                if (!isLoading && email && password) {
                  e.currentTarget.style.background = 'var(--cgiar-green)';
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = 'none';
                }
              }}
            >
              {isLoading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          {/* Footer */}
          <div
            style={{
              marginTop: 'var(--space-2xl)',
              paddingTop: 'var(--space-lg)',
              borderTop: '1px solid var(--cgiar-gray)',
              textAlign: 'center',
            }}
          >
            <p
              style={{
                fontSize: '0.8125rem',
                color: 'var(--color-text-muted)',
              }}
            >
              CGIAR Partner Request Support System
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
};
