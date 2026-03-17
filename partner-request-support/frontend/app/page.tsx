'use client';

import { useState, useEffect } from 'react';
import { Upload, FileSpreadsheet, CheckCircle2, XCircle, Globe, Database, BarChart3, Search, ChevronDown, ChevronUp, Info, RefreshCw, Cloud, ThumbsUp, ThumbsDown, AlertCircle, Eye, EyeOff } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { SyncAlert } from './components/SyncAlert';

interface ClarisaMatch {
  clarisa_id: string;
  name: string;
  acronym: string;
  countries: string[];
  institution_type: string;
  website: string;
  scores: {
    cosine_similarity: number;
    fuzz_name_score: number;
    fuzz_acronym_score: number;
    final_score: number;
  };
}

interface WebSearch {
  success: boolean;
  result?: string;
  error?: string;
}

interface Partner {
  id: string;
  name: string;
  acronym: string;
  website: string;
  country: string;
  match_found: boolean;
  clarisa_match: ClarisaMatch | null;
  top_candidates: ClarisaMatch[];
  web_search: WebSearch | null;
  match_quality: 'excellent' | 'good' | 'fair' | 'no_match' | 'error';
  api_data?: {
    request_id: number;
    request_source: string;
    external_user: string;
    created_at: string;
  };
}

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

interface ProcessingResults {
  partners: Partner[];
  stats: {
    total: number;
    matched: number;
    no_match: number;
    web_search_attempted: number;
    web_search_success: number;
    errors: number;
    excellent: number;
    good: number;
    fair: number;
    matched_percentage: number;
    no_match_percentage: number;
  };
  sync_info?: SyncInfo;
  cache_info?: {
    total_requests: number;
    cache_hits: number;
    cache_misses: number;
    from_cache: boolean;
    processed_new: boolean;
  };
}

interface ApiPartnerRequest {
  id: number;
  partnerName: string;
  acronym: string;
  webPage: string | null;
  requestStatus: string;
  requestSource: string;
  externalUserName: string;
  created_at: string;
  countryDTO: {
    name: string;
    isoAlpha2: string;
  };
  institutionTypeDTO: {
    name: string;
  };
}

interface AuthUser {
  id: number;
  username: string;
  name: string;
  email: string;
  permissions: string[];
}

interface AuthResponse {
  access_token: string;
  user: AuthUser;
}

export default function Home() {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const [file, setFile] = useState<File | null>(null);
  const [processing, setProcessing] = useState(false);
  const [results, setResults] = useState<ProcessingResults | null>(null);
  const [message, setMessage] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [modalType, setModalType] = useState<'clarisa' | 'websearch' | 'candidates' | 'accept' | 'reject' | null>(null);
  const [selectedPartner, setSelectedPartner] = useState<Partner | null>(null);
  const [showQualityInfo, setShowQualityInfo] = useState(false);
  const [uploadMode, setUploadMode] = useState<'excel' | 'api'>('excel');
  const [apiPartners, setApiPartners] = useState<ApiPartnerRequest[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [rejectJustification, setRejectJustification] = useState('');
  const [respondingToRequest, setRespondingToRequest] = useState(false);
  const [responseMessage, setResponseMessage] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [runningWebSearch, setRunningWebSearch] = useState<{ [partnerId: string]: boolean }>({});
  
  // Authentication states
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loggingIn, setLoggingIn] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  // Handle login
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoggingIn(true);
    setLoginError(null);

    try {
      const response = await axios.post<AuthResponse>(
        'https://clarisatest-back.ciat.cgiar.org/auth/login',
        {
          login: loginEmail,
          password: loginPassword
        },
        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      const { access_token, user } = response.data;
      
      setAuthToken(access_token);
      setAuthUser(user);
      setIsAuthenticated(true);
      setLoginError(null);

      // Clear login form
      setLoginPassword('');
      
    } catch (err: any) {
      let errorMsg = 'Unable to sign in. Please try again.';
      
      if (err.response) {
        // Server responded with error
        const status = err.response.status;
        
        if (status === 401 || status === 403) {
          errorMsg = 'Invalid email or password. Please check your credentials.';
        } else if (status === 500) {
          errorMsg = 'Invalid credentials. Please verify your email and password.';
        } else if (status >= 500) {
          errorMsg = 'Authentication service is temporarily unavailable. Please try again later.';
        } else {
          // Try to get a message from the response
          const responseMsg = err.response.data?.message || err.response.data?.detail;
          if (responseMsg && responseMsg !== 'Http Exception' && !responseMsg.includes('Exception')) {
            errorMsg = responseMsg;
          }
        }
      } else if (err.request) {
        // Request made but no response received
        errorMsg = 'Unable to connect to authentication service. Please check your internet connection.';
      }
      
      setLoginError(errorMsg);
    } finally {
      setLoggingIn(false);
    }
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setAuthUser(null);
    setAuthToken(null);
    setResults(null);
    setFile(null);
    setApiPartners([]);
  };

  // Sync partner requests on component mount (only if authenticated)
  useEffect(() => {
    if (isAuthenticated) {
      syncPartnerRequests();
    }
  }, [isAuthenticated]);

  const syncPartnerRequests = async () => {
    setSyncing(true);
    setSyncError(null);
    
    try {
      const response = await axios.get(`${API_URL}/api/sync-partner-requests`);
      setApiPartners(response.data.pending_requests || []);
    } catch (err: any) {
      setSyncError(err.response?.data?.detail || 'Error syncing partner requests');
      console.error('Sync error:', err);
    } finally {
      setSyncing(false);
    }
  };

  const handleProcessApiPartners = async () => {
    setProcessing(true);
    setError(null);
    setMessage('Synchronizing CLARISA database...');

    try {
      const response = await axios.post<ProcessingResults>(
        `${API_URL}/api/process-api-partners`,
        null,  // Will process first 5 by default
        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      setResults(response.data);
      setMessage('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error processing API partners. Please try again.');
      setMessage('');
    } finally {
      setProcessing(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
      setResults(null);
    }
  };

  const handleDownloadTemplate = async () => {
    try {
      const response = await axios.get(
        `${API_URL}/api/download-template`,
        {
          responseType: 'blob',
        }
      );

      // Create a blob from the response
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });

      // Create a download link and trigger download
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'PartnerRequestTemplate_v1.xlsx';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      console.error('Error downloading template:', err);
      setError('Failed to download template. Please try again.');
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file first');
      return;
    }

    if (!authToken || !authUser) {
      setError('Authentication required. Please login first.');
      return;
    }

    setProcessing(true);
    setError(null);
    setMessage('Synchronizing CLARISA database...');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_email', authUser.email);
    formData.append('user_name', authUser.name);
    formData.append('auth_token', authToken);
    formData.append('create_requests', 'true');

    try {
      const response = await axios.post<ProcessingResults>(
        `${API_URL}/api/process-partners`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      setResults(response.data);
      setMessage('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error processing file. Please try again.');
      setMessage('');
    } finally {
      setProcessing(false);
    }
  };

  const handleAcceptRequest = async () => {
    if (!selectedPartner?.api_data?.request_id) {
      setResponseMessage({ type: 'error', message: 'No request ID available' });
      return;
    }

    if (!authToken || !authUser) {
      setResponseMessage({ type: 'error', message: 'Authentication required' });
      return;
    }

    setRespondingToRequest(true);
    setResponseMessage(null);

    try {
      const response = await axios.post(
        `${API_URL}/api/respond-partner-request`,
        {
          request_id: selectedPartner.api_data.request_id,
          user_id: authUser.id,
          accept: true,
          auth_token: authToken
        },
        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      setResponseMessage({ 
        type: 'success', 
        message: `Partner request for "${selectedPartner.name}" successfully accepted!` 
      });
      
      // Remove from results
      if (results) {
        const updatedPartners = results.partners.filter(
          p => p.api_data?.request_id !== selectedPartner.api_data?.request_id
        );
        setResults({
          ...results,
          partners: updatedPartners,
          stats: {
            ...results.stats,
            total: updatedPartners.length
          }
        });
      }

      // Close modal after short delay
      setTimeout(() => {
        setModalOpen(false);
        setSelectedPartner(null);
        setResponseMessage(null);
      }, 2000);

    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Error accepting partner request';
      setResponseMessage({ type: 'error', message: errorMsg });
    } finally {
      setRespondingToRequest(false);
    }
  };

  const handleRejectRequest = async () => {
    if (!selectedPartner?.api_data?.request_id) {
      setResponseMessage({ type: 'error', message: 'No request ID available' });
      return;
    }

    if (!authToken || !authUser) {
      setResponseMessage({ type: 'error', message: 'Authentication required' });
      return;
    }

    setRespondingToRequest(true);
    setResponseMessage(null);

    try {
      const response = await axios.post(
        `${API_URL}/api/respond-partner-request`,
        {
          request_id: selectedPartner.api_data.request_id,
          user_id: authUser.id,
          accept: false,
          reject_justification: rejectJustification.trim() || 'No justification provided',
          auth_token: authToken
        },
        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      setResponseMessage({ 
        type: 'success', 
        message: `Partner request for "${selectedPartner.name}" successfully rejected.` 
      });
      
      // Remove from results
      if (results) {
        const updatedPartners = results.partners.filter(
          p => p.api_data?.request_id !== selectedPartner.api_data?.request_id
        );
        setResults({
          ...results,
          partners: updatedPartners,
          stats: {
            ...results.stats,
            total: updatedPartners.length
          }
        });
      }

      // Close modal after short delay
      setTimeout(() => {
        setModalOpen(false);
        setSelectedPartner(null);
        setRejectJustification('');
        setResponseMessage(null);
      }, 2000);

    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Error rejecting partner request';
      setResponseMessage({ type: 'error', message: errorMsg });
    } finally {
      setRespondingToRequest(false);
    }
  };

  const handleManualWebSearch = async (partner: Partner) => {
    const partnerId = partner.id;
    
    setRunningWebSearch(prev => ({ ...prev, [partnerId]: true }));
    
    try {
      const response = await axios.post(
        `${API_URL}/api/manual-web-search`,
        {
          partner_name: partner.name,
          country: partner.country || null,
          website: partner.website || null
        },
        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      // Update the partner in results with the web search data
      if (results) {
        const updatedPartners = results.partners.map(p => 
          p.id === partnerId
            ? { ...p, web_search: response.data }
            : p
        );
        
        setResults({
          ...results,
          partners: updatedPartners,
          stats: {
            ...results.stats,
            web_search_attempted: results.stats.web_search_attempted + 1,
            web_search_success: response.data.success 
              ? results.stats.web_search_success + 1 
              : results.stats.web_search_success
          }
        });

        // If successful, open the modal automatically
        if (response.data.success) {
          const updatedPartner = { ...partner, web_search: response.data };
          setSelectedPartner(updatedPartner);
          setModalType('websearch');
          setModalOpen(true);
        }
      }
    } catch (err: any) {
      console.error('Error running manual web search:', err);
      setError(err.response?.data?.detail || 'Error running web search. Please try again.');
    } finally {
      setRunningWebSearch(prev => ({ ...prev, [partnerId]: false }));
    }
  };

  const getQualityColor = (quality: string) => {
    switch (quality) {
      case 'excellent': return 'var(--color-excellent)';
      case 'good': return 'var(--color-good)';
      case 'fair': return 'var(--color-fair)';
      case 'no_match': return 'var(--color-no-match)';
      default: return 'var(--color-error)';
    }
  };

  const getQualityBadge = (quality: string) => {
    const config = {
      excellent: { label: 'Excellent', icon: <CheckCircle2 size={16} /> },
      good: { label: 'Good', icon: <CheckCircle2 size={16} /> },
      fair: { label: 'Fair', icon: <CheckCircle2 size={16} /> },
      no_match: { label: 'No Match', icon: <XCircle size={16} /> },
      error: { label: 'Error', icon: <XCircle size={16} /> },
    };
    return config[quality as keyof typeof config] || config.error;
  };

  const filteredPartners = results?.partners.filter(partner =>
    partner.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    partner.acronym?.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  // Show login screen if not authenticated
  if (!isAuthenticated) {
    return (
      <div style={{ 
        minHeight: '100vh', 
        background: 'var(--color-background)',
        display: 'flex',
      }}>
        {/* Left Side - Branding */}
        <div style={{
          flex: '1',
          background: 'linear-gradient(135deg, var(--cgiar-navy) 0%, #1a4d2e 100%)',
          padding: 'var(--space-2xl)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          position: 'relative',
          overflow: 'hidden',
        }}>
          {/* Decorative circles */}
          <div style={{
            position: 'absolute',
            width: '400px',
            height: '400px',
            borderRadius: '50%',
            background: 'rgba(16, 185, 129, 0.1)',
            top: '-200px',
            left: '-200px',
          }} />
          <div style={{
            position: 'absolute',
            width: '300px',
            height: '300px',
            borderRadius: '50%',
            background: 'rgba(16, 185, 129, 0.15)',
            bottom: '-150px',
            right: '-150px',
          }} />

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
            {/* Logo */}
            <div style={{
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
            }}>
              <FileSpreadsheet size={60} color="white" />
            </div>

            <h1 style={{
              fontSize: '2.5rem',
              fontWeight: 700,
              color: 'white',
              marginBottom: 'var(--space-md)',
              lineHeight: 1.2,
            }}>
              Partner Request Support
            </h1>
            <p style={{
              fontSize: '1.125rem',
              color: 'rgba(255, 255, 255, 0.8)',
              lineHeight: 1.6,
            }}>
              Streamline institutional matching and partner request management with AI-powered analysis
            </p>

            {/* Features */}
            <div style={{
              marginTop: 'var(--space-2xl)',
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-md)',
              textAlign: 'left',
            }}>
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
        <div style={{
          flex: '1',
          padding: 'var(--space-2xl)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'white',
        }}>
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
              <h2 style={{
                fontSize: '1.875rem',
                fontWeight: 700,
                color: 'var(--cgiar-navy)',
                marginBottom: 'var(--space-xs)',
              }}>
                Welcome back
              </h2>
              <p style={{
                fontSize: '0.9375rem',
                color: 'var(--color-text-muted)',
              }}>
                Sign in to your account to continue
              </p>
            </div>

            {/* Login Form */}
            <form onSubmit={handleLogin}>
              <div style={{ marginBottom: 'var(--space-lg)' }}>
                <label style={{
                  display: 'block',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  color: 'var(--cgiar-navy)',
                  marginBottom: 'var(--space-xs)',
                }}>
                  Email
                </label>
                <input
                  type="email"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  placeholder="your.email@cgiar.org"
                  required
                  disabled={loggingIn}
                  style={{
                    width: '100%',
                    padding: '14px var(--space-md)',
                    border: '1px solid var(--cgiar-gray)',
                    borderRadius: 'var(--radius-md)',
                    fontSize: '0.9375rem',
                    fontFamily: 'inherit',
                    transition: 'all 0.2s',
                    background: loggingIn ? 'var(--cgiar-light-gray)' : 'white',
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
                <label style={{
                  display: 'block',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  color: 'var(--cgiar-navy)',
                  marginBottom: 'var(--space-xs)',
                }}>
                  Password
                </label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showPassword ? "text" : "password"}
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    placeholder="Enter your password"
                    required
                    disabled={loggingIn}
                    style={{
                      width: '100%',
                      padding: '14px var(--space-md)',
                      paddingRight: '48px',
                      border: '1px solid var(--cgiar-gray)',
                      borderRadius: 'var(--radius-md)',
                      fontSize: '0.9375rem',
                      fontFamily: 'inherit',
                      transition: 'all 0.2s',
                      background: loggingIn ? 'var(--cgiar-light-gray)' : 'white',
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
                    disabled={loggingIn}
                    style={{
                      position: 'absolute',
                      right: '12px',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      background: 'none',
                      border: 'none',
                      cursor: loggingIn ? 'not-allowed' : 'pointer',
                      padding: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'var(--color-text-muted)',
                      transition: 'color 0.2s',
                      opacity: loggingIn ? 0.5 : 1,
                    }}
                    onMouseOver={(e) => !loggingIn && (e.currentTarget.style.color = 'var(--cgiar-navy)')}
                    onMouseOut={(e) => !loggingIn && (e.currentTarget.style.color = 'var(--color-text-muted)')}
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
                disabled={loggingIn || !loginEmail || !loginPassword}
                style={{
                  width: '100%',
                  padding: '14px var(--space-lg)',
                  background: loggingIn || !loginEmail || !loginPassword 
                    ? 'var(--cgiar-gray)' 
                    : 'var(--cgiar-green)',
                  color: 'white',
                  border: 'none',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '1rem',
                  fontWeight: 600,
                  cursor: loggingIn || !loginEmail || !loginPassword ? 'not-allowed' : 'pointer',
                  transition: 'all 0.2s',
                }}
                onMouseOver={(e) => {
                  if (!loggingIn && loginEmail && loginPassword) {
                    e.currentTarget.style.background = '#059669';
                    e.currentTarget.style.transform = 'translateY(-1px)';
                    e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                  }
                }}
                onMouseOut={(e) => {
                  if (!loggingIn && loginEmail && loginPassword) {
                    e.currentTarget.style.background = 'var(--cgiar-green)';
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = 'none';
                  }
                }}
              >
                {loggingIn ? 'Signing in...' : 'Sign In'}
              </button>
            </form>

            {/* Footer */}
            <div style={{
              marginTop: 'var(--space-2xl)',
              paddingTop: 'var(--space-lg)',
              borderTop: '1px solid var(--cgiar-gray)',
              textAlign: 'center',
            }}>
              <p style={{
                fontSize: '0.8125rem',
                color: 'var(--color-text-muted)',
              }}>
                CGIAR Partner Request Support System
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--color-background)' }}>
      {/* Modern Header */}
      <header style={{
        background: 'white',
        borderBottom: '1px solid var(--cgiar-gray)',
        boxShadow: 'var(--shadow-sm)',
      }}>
        <div style={{
          maxWidth: '1400px',
          margin: '0 auto',
          padding: 'var(--space-sm) var(--space-lg)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}
          >
            <div style={{
              width: '40px',
              height: '40px',
              background: 'var(--cgiar-green)',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <FileSpreadsheet size={24} color="white" />
            </div>
            <div>
              <h1 style={{
                fontSize: '1.25rem',
                fontWeight: 600,
                color: 'var(--cgiar-navy)',
                marginBottom: '2px',
              }}>
                Partner Request Support
              </h1>
              <p style={{
                fontSize: '0.75rem',
                color: 'var(--color-text-muted)',
                fontWeight: 400,
              }}>
                CGIAR Institutional Mapping
              </p>
            </div>
          </motion.div>

          {/* Testing Environment Tag */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            style={{
              background: '#DC2626',
              color: 'white',
              padding: '8px 20px',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.875rem',
              fontWeight: 600,
              boxShadow: '0 2px 8px rgba(220, 38, 38, 0.25)',
              letterSpacing: '0.5px',
            }}
          >
            Testing Environment
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
            <div style={{
              textAlign: 'right',
              marginRight: 'var(--space-sm)',
            }}>
              <p style={{
                fontSize: '0.875rem',
                fontWeight: 600,
                color: 'var(--cgiar-navy)',
                marginBottom: '2px',
              }}>
                {authUser?.name || authUser?.username}
              </p>
              <p style={{
                fontSize: '0.75rem',
                color: 'var(--color-text-muted)',
              }}>
                {authUser?.email}
              </p>
            </div>
            <button
              onClick={handleLogout}
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

      <main style={{
        maxWidth: '1400px',
        margin: '0 auto',
        padding: 'var(--space-lg) var(--space-lg)',
      }}>
        {/* AI Disclaimer */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          style={{
            background: 'linear-gradient(135deg, #FFFBF0 0%, #FFF9E6 100%)',
            border: '1px solid #FFE8A3',
            borderLeft: '4px solid var(--cgiar-yellow)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-sm) var(--space-md)',
            marginBottom: 'var(--space-lg)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-sm)',
          }}
        >
          <span style={{ fontSize: '1.25rem' }}>🤖</span>
          <p style={{
            fontSize: '0.73rem',
            color: 'var(--cgiar-navy)',
            lineHeight: 1.5,
            margin: 0,
          }}>
            <strong>AI-Powered Analysis:</strong> This tool uses artificial intelligence to match partner institutions with CGIAR's database and perform web verification. Results are automated suggestions that may require human validation.
          </p>
        </motion.div>

        {/* Upload Section */}
        {!results && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div style={{
              background: 'white',
              borderRadius: 'var(--radius-xl)',
              padding: 'var(--space-md)',
              boxShadow: 'var(--shadow-md)',
              maxWidth: '700px',
              margin: '0 auto',
            }}>
              {/* Upload Header */}
              <div style={{ textAlign: 'center', marginBottom: 'var(--space-md)' }}>
                <h2 style={{
                  fontSize: '1.25rem',
                  fontWeight: 600,
                  color: 'var(--cgiar-navy)',
                  marginBottom: 'var(--space-xs)',
                }}>
                  Process Partner Requests
                </h2>
                <p style={{
                  fontSize: '0.875rem',
                  color: 'var(--color-text-muted)',
                }}>
                  Match partners with the CLARISA database using AI
                </p>
              </div>

              {/* Mode Selector */}
              <div style={{
                display: 'flex',
                gap: 'var(--space-sm)',
                marginBottom: 'var(--space-md)',
                background: 'var(--cgiar-light-gray)',
                padding: '4px',
                borderRadius: 'var(--radius-md)',
              }}>
                <button
                  onClick={() => setUploadMode('excel')}
                  style={{
                    flex: 1,
                    padding: 'var(--space-sm)',
                    background: uploadMode === 'excel' ? 'white' : 'transparent',
                    color: uploadMode === 'excel' ? 'var(--cgiar-navy)' : 'var(--color-text-muted)',
                    border: 'none',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.875rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    boxShadow: uploadMode === 'excel' ? 'var(--shadow-sm)' : 'none',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px',
                  }}
                >
                  <Upload size={16} />
                  Upload Excel
                </button>
                <button
                  onClick={() => setUploadMode('api')}
                  style={{
                    flex: 1,
                    padding: 'var(--space-sm)',
                    background: uploadMode === 'api' ? 'white' : 'transparent',
                    color: uploadMode === 'api' ? 'var(--cgiar-navy)' : 'var(--color-text-muted)',
                    border: 'none',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.875rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    boxShadow: uploadMode === 'api' ? 'var(--shadow-sm)' : 'none',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px',
                  }}
                >
                  <Cloud size={16} />
                  API Requests {apiPartners.length > 0 && `(${apiPartners.length})`}
                </button>
              </div>

              {/* Excel Mode */}
              {uploadMode === 'excel' && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.3 }}
                >
                  {/* Upload Zone */}
                  <div style={{
                    border: `2px dashed ${file ? 'var(--cgiar-green)' : 'var(--cgiar-gray)'}`,
                    borderRadius: 'var(--radius-lg)',
                    padding: 'var(--space-md)',
                    textAlign: 'center',
                    background: file ? '#F0F9E8' : 'var(--cgiar-light-gray)',
                    transition: 'all 0.3s ease',
                    cursor: 'pointer',
                    marginBottom: 'var(--space-md)',
                  }}>
                    <input
                      type="file"
                      accept=".xlsx,.xls"
                      onChange={handleFileChange}
                      style={{ display: 'none' }}
                      id="file-upload"
                    />
                    <label
                      htmlFor="file-upload"
                      style={{ cursor: 'pointer', display: 'block' }}
                    >
                      <Upload
                        size={40}
                        style={{
                          color: file ? 'var(--cgiar-green)' : 'var(--color-text-muted)',
                          margin: '0 auto var(--space-sm)',
                        }}
                      />
                      {file ? (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                          <p style={{
                            fontSize: '0.9375rem',
                            fontWeight: 600,
                            color: 'var(--cgiar-green)',
                            marginBottom: 'var(--space-xs)',
                          }}>
                            {file.name}
                          </p>
                          <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                            Click to change file
                          </p>
                        </motion.div>
                      ) : (
                        <div>
                          <p style={{
                            fontSize: '0.9375rem',
                            fontWeight: 500,
                            color: 'var(--cgiar-navy)',
                            marginBottom: 'var(--space-xs)',
                          }}>
                            Drop your Excel file here
                          </p>
                          <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                            or click to browse
                          </p>
                        </div>
                      )}
                    </label>
                  </div>

                  {/* Process Button */}
                  <button
                    onClick={handleUpload}
                    disabled={!file || processing}
                    style={{
                      width: '100%',
                      padding: 'var(--space-sm) var(--space-md)',
                      background: file && !processing
                        ? 'linear-gradient(135deg, var(--cgiar-green) 0%, #629600 100%)'
                        : 'var(--cgiar-gray)',
                      color: file && !processing ? 'white' : 'var(--color-text-muted)',
                      borderRadius: 'var(--radius-md)',
                      fontSize: '0.9375rem',
                      fontWeight: 600,
                      cursor: file && !processing ? 'pointer' : 'not-allowed',
                      transition: 'all 0.3s ease',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 'var(--space-sm)',
                      border: 'none',
                      boxShadow: file && !processing ? 'var(--shadow-md)' : 'none',
                    }}
                    onMouseOver={(e) => {
                      if (file && !processing) e.currentTarget.style.transform = 'translateY(-2px)';
                    }}
                    onMouseOut={(e) => {
                      if (file && !processing) e.currentTarget.style.transform = 'translateY(0)';
                    }}
                  >
                    {processing ? (
                      <>
                        <div className="spinner" />
                        {message || 'Processing...'}
                      </>
                    ) : (
                      <>
                        <BarChart3 size={18} />
                        Analyze Partners
                      </>
                    )}
                  </button>

                  {/* Recommendation Text */}
                  <p style={{
                    marginTop: 'var(--space-xs)',
                    fontSize: '0.75rem',
                    color: 'var(--color-text-muted)',
                    textAlign: 'center',
                    fontStyle: 'italic',
                  }}>
                    <strong>Recommendation:</strong> Upload a maximum of 10 partners in a single file for optimal processing.
                  </p>

                  {/* Info Box */}
                  <div style={{
                    marginTop: 'var(--space-md)',
                    padding: 'var(--space-md)',
                    background: '#E8F4FD',
                    borderRadius: 'var(--radius-md)',
                    borderLeft: '3px solid var(--cgiar-blue)',
                  }}>
                    <h4 style={{
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      color: 'var(--cgiar-blue)',
                      marginBottom: 'var(--space-xs)',
                    }}>
                      Required Excel Format
                    </h4>
                    
                    <ul style={{
                      paddingLeft: 'var(--space-md)',
                      color: 'var(--color-text-secondary)',
                      fontSize: '0.75rem',
                      lineHeight: 1.6,
                      marginBottom: 'var(--space-sm)',
                    }}>
                      <li><strong>Column 0:</strong> ID <span style={{color: '#DC2626', fontWeight: 600}}>(required)</span></li>
                      <li><strong>Column 1:</strong> Partner Name <span style={{color: '#DC2626', fontWeight: 600}}>(required)</span></li>
                      <li><strong>Column 2:</strong> Acronym (optional)</li>
                      <li><strong>Column 3:</strong> Website (optional)</li>
                      <li><strong>Column 4:</strong> Institution Type <span style={{color: '#DC2626', fontWeight: 600}}>(required)</span></li>
                      <li><strong>Column 5:</strong> Country <span style={{color: '#DC2626', fontWeight: 600}}>(required)</span></li>
                      <li><strong>Column 6:</strong> Category 1 (optional)</li>
                      <li><strong>Column 7:</strong> Category 2 (optional)</li>
                    </ul>

                    {/* Download Template Button */}
                    <button
                      onClick={handleDownloadTemplate}
                      style={{
                        width: '100%',
                        padding: '8px 12px',
                        background: 'var(--cgiar-blue)',
                        color: 'white',
                        border: 'none',
                        borderRadius: 'var(--radius-md)',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '6px',
                      }}
                      onMouseOver={(e) => {
                        e.currentTarget.style.background = '#1e5a8e';
                        e.currentTarget.style.transform = 'translateY(-1px)';
                      }}
                      onMouseOut={(e) => {
                        e.currentTarget.style.background = 'var(--cgiar-blue)';
                        e.currentTarget.style.transform = 'translateY(0)';
                      }}
                    >
                      <FileSpreadsheet size={14} />
                      Download Excel Template
                    </button>
                  </div>
                </motion.div>
              )}

              {/* API Mode */}
              {uploadMode === 'api' && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.3 }}
                >
                  {/* API Status */}
                  <div style={{
                    background: syncing ? '#F0F9E8' : apiPartners.length > 0 ? '#E8F4FD' : '#FEF3E8',
                    border: `1px solid ${syncing ? 'var(--cgiar-green)' : apiPartners.length > 0 ? 'var(--cgiar-blue)' : 'var(--cgiar-yellow)'}`,
                    borderRadius: 'var(--radius-md)',
                    padding: 'var(--space-md)',
                    marginBottom: 'var(--space-md)',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-xs)' }}>
                      <h4 style={{
                        fontSize: '0.875rem',
                        fontWeight: 600,
                        color: 'var(--cgiar-navy)',
                      }}>
                        {syncing ? 'Syncing...' : apiPartners.length > 0 ? `${apiPartners.length} Pending Partner Requests` : 'No Partner Requests'}
                      </h4>
                      <button
                        onClick={syncPartnerRequests}
                        disabled={syncing}
                        style={{
                          padding: '4px 10px',
                          background: 'white',
                          border: '1px solid var(--cgiar-gray)',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: '0.75rem',
                          fontWeight: 500,
                          cursor: syncing ? 'not-allowed' : 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          color: 'var(--cgiar-navy)',
                          transition: 'all 0.2s',
                        }}
                        onMouseOver={(e) => {
                          if (!syncing) e.currentTarget.style.background = 'var(--cgiar-light-gray)';
                        }}
                        onMouseOut={(e) => {
                          if (!syncing) e.currentTarget.style.background = 'white';
                        }}
                      >
                        <RefreshCw size={12} style={{ animation: syncing ? 'spin 1s linear infinite' : 'none' }} />
                        Refresh
                      </button>
                    </div>
                    <p style={{
                      fontSize: '0.75rem',
                      color: 'var(--color-text-secondary)',
                      lineHeight: 1.5,
                    }}>
                      {syncing ? 'Fetching partner requests from CLARISA API...' : 
                       apiPartners.length > 0 ? `Ready to process first 3 partner requests (testing mode)` : 
                       'Click Refresh to sync with CLARISA API'}
                    </p>
                  </div>

                  {syncError && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      style={{
                        marginBottom: 'var(--space-md)',
                        padding: 'var(--space-sm)',
                        background: '#FEE',
                        border: '1px solid var(--color-error)',
                        borderRadius: 'var(--radius-md)',
                        color: 'var(--color-error)',
                        fontSize: '0.75rem',
                      }}
                    >
                      {syncError}
                    </motion.div>
                  )}

                  {/* Process Button */}
                  <button
                    onClick={handleProcessApiPartners}
                    disabled={apiPartners.length === 0 || processing}
                    style={{
                      width: '100%',
                      padding: 'var(--space-sm) var(--space-md)',
                      background: apiPartners.length > 0 && !processing
                        ? 'linear-gradient(135deg, var(--cgiar-blue) 0%, #0052A3 100%)'
                        : 'var(--cgiar-gray)',
                      color: apiPartners.length > 0 && !processing ? 'white' : 'var(--color-text-muted)',
                      borderRadius: 'var(--radius-md)',
                      fontSize: '0.9375rem',
                      fontWeight: 600,
                      cursor: apiPartners.length > 0 && !processing ? 'pointer' : 'not-allowed',
                      transition: 'all 0.3s ease',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 'var(--space-sm)',
                      border: 'none',
                      boxShadow: apiPartners.length > 0 && !processing ? 'var(--shadow-md)' : 'none',
                    }}
                    onMouseOver={(e) => {
                      if (apiPartners.length > 0 && !processing) e.currentTarget.style.transform = 'translateY(-2px)';
                    }}
                    onMouseOut={(e) => {
                      if (apiPartners.length > 0 && !processing) e.currentTarget.style.transform = 'translateY(0)';
                    }}
                  >
                    {processing ? (
                      <>
                        <div className="spinner" />
                        {message || 'Processing...'}
                      </>
                    ) : (
                      <>
                        <BarChart3 size={18} />
                        Process Partner Requests
                      </>
                    )}
                  </button>

                  {/* Info Box */}
                  <div style={{
                    marginTop: 'var(--space-md)',
                    padding: 'var(--space-md)',
                    background: '#FFF4E6',
                    borderRadius: 'var(--radius-md)',
                    borderLeft: '3px solid var(--cgiar-yellow)',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'start', gap: 'var(--space-xs)' }}>
                      <Info size={16} style={{ color: 'var(--cgiar-yellow)', marginTop: '2px', flexShrink: 0 }} />
                      <div>
                        <h4 style={{
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          color: 'var(--cgiar-navy)',
                          marginBottom: '4px',
                        }}>
                          Testing Mode
                        </h4>
                        <p style={{
                          fontSize: '0.75rem',
                          color: 'var(--color-text-secondary)',
                          lineHeight: 1.5,
                          margin: 0,
                        }}>
                          Currently processing first 3 partner requests for testing. Full processing will be available in production mode.
                        </p>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}

              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  style={{
                    marginTop: 'var(--space-md)',
                    padding: 'var(--space-sm)',
                    background: '#FEE',
                    border: '1px solid var(--color-error)',
                    borderRadius: 'var(--radius-md)',
                    color: 'var(--color-error)',
                    fontSize: '0.75rem',
                  }}
                >
                  {error}
                </motion.div>
              )}
            </div>
          </motion.div>
        )}

        {/* Results Section */}
        {results && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
          >
            {/* Sync Info Alert */}
            {results.sync_info && (
              <SyncAlert syncInfo={results.sync_info} className="mb-4" />
            )}

            {/* Statistics Grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: 'var(--space-sm)',
              marginBottom: 'var(--space-lg)',
            }}>
              <StatCard
                title="Total Partners"
                value={results.stats.total}
                color="var(--cgiar-navy)"
                icon={<FileSpreadsheet size={20} />}
              />
              <StatCard
                title="Matched"
                value={results.stats.matched}
                percentage={results.stats.matched_percentage}
                color="var(--cgiar-green)"
                icon={<CheckCircle2 size={20} />}
              />
              <StatCard
                title="Excellent Matches"
                value={results.stats.excellent}
                color="var(--color-excellent)"
                icon={<Database size={20} />}
              />
              <StatCard
                title="Web Searches"
                value={results.stats.web_search_success}
                subtitle={`${results.stats.web_search_attempted} attempted`}
                color="var(--cgiar-blue)"
                icon={<Globe size={20} />}
              />
            </div>

            {/* Results Header */}
            <div style={{
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
            }}>
              <div>
                <h2 style={{
                  fontSize: '1.25rem',
                  fontWeight: 600,
                  color: 'var(--cgiar-navy)',
                  marginBottom: '2px',
                }}>
                  Partner Results
                </h2>
                <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                  {filteredPartners?.length} partners {searchQuery && `matching "${searchQuery}"`}
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
                  onClick={() => {
                    setResults(null);
                    setFile(null);
                    setSearchQuery('');
                  }}
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
            <div style={{
              background: 'white',
              borderRadius: 'var(--radius-md)',
              boxShadow: 'var(--shadow-sm)',
              overflow: 'hidden',
            }}>
              <div style={{ overflowX: 'auto' }}>
                <table style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  fontSize: '0.8125rem',
                }}>
                  <thead>
                    <tr style={{
                      background: 'var(--cgiar-light-gray)',
                      borderBottom: '2px solid var(--cgiar-gray)',
                    }}>
                      <th style={{
                        padding: 'var(--space-sm) var(--space-md)',
                        textAlign: 'left',
                        fontWeight: 600,
                        color: 'var(--cgiar-navy)',
                        fontSize: '0.75rem',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                      }}>Partner Name</th>
                      <th style={{
                        padding: 'var(--space-sm) var(--space-md)',
                        textAlign: 'left',
                        fontWeight: 600,
                        color: 'var(--cgiar-navy)',
                        fontSize: '0.75rem',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                      }}>Acronym</th>
                      <th style={{
                        padding: 'var(--space-sm) var(--space-md)',
                        textAlign: 'left',
                        fontWeight: 600,
                        color: 'var(--cgiar-navy)',
                        fontSize: '0.75rem',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                      }}>Country</th>
                      <th style={{
                        padding: 'var(--space-sm) var(--space-md)',
                        textAlign: 'center',
                        fontWeight: 600,
                        color: 'var(--cgiar-navy)',
                        fontSize: '0.75rem',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                        position: 'relative',
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}>
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
                                  <div style={{
                                    fontWeight: 600,
                                    color: 'var(--cgiar-navy)',
                                    marginBottom: '6px',
                                    fontSize: '0.8125rem',
                                  }}>
                                    Match Quality Levels
                                  </div>
                                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                      <div style={{
                                        width: '8px',
                                        height: '8px',
                                        borderRadius: '50%',
                                        background: 'var(--color-excellent)',
                                      }} />
                                      <span style={{ color: 'var(--color-text-secondary)' }}>
                                        <strong>Excellent</strong> (≥85%): High confidence match
                                      </span>
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                      <div style={{
                                        width: '8px',
                                        height: '8px',
                                        borderRadius: '50%',
                                        background: 'var(--color-good)',
                                      }} />
                                      <span style={{ color: 'var(--color-text-secondary)' }}>
                                        <strong>Good</strong> (≥70%): Strong match
                                      </span>
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                      <div style={{
                                        width: '8px',
                                        height: '8px',
                                        borderRadius: '50%',
                                        background: 'var(--color-fair)',
                                      }} />
                                      <span style={{ color: 'var(--color-text-secondary)' }}>
                                        <strong>Fair</strong> (≥60%): Moderate match
                                      </span>
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                      <div style={{
                                        width: '8px',
                                        height: '8px',
                                        borderRadius: '50%',
                                        background: 'var(--color-no-match)',
                                      }} />
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
                      <th style={{
                        padding: 'var(--space-sm) var(--space-md)',
                        textAlign: 'center',
                        fontWeight: 600,
                        color: 'var(--cgiar-navy)',
                        fontSize: '0.75rem',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                      }}>CLARISA</th>
                      <th style={{
                        padding: 'var(--space-sm) var(--space-md)',
                        textAlign: 'center',
                        fontWeight: 600,
                        color: 'var(--cgiar-navy)',
                        fontSize: '0.75rem',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                      }}>Top Candidates</th>
                      <th style={{
                        padding: 'var(--space-sm) var(--space-md)',
                        textAlign: 'center',
                        fontWeight: 600,
                        color: 'var(--cgiar-navy)',
                        fontSize: '0.75rem',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                      }}>Web Search</th>
                      <th style={{
                        padding: 'var(--space-sm) var(--space-md)',
                        textAlign: 'center',
                        fontWeight: 600,
                        color: 'var(--cgiar-navy)',
                        fontSize: '0.75rem',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                      }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredPartners?.map((partner, index) => {
                      const badge = getQualityBadge(partner.match_quality);
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
                          onMouseOver={(e) => e.currentTarget.style.background = '#FAFBFC'}
                          onMouseOut={(e) => e.currentTarget.style.background = 'white'}
                        >
                          <td style={{
                            padding: 'var(--space-sm) var(--space-md)',
                            color: 'var(--cgiar-navy)',
                            fontWeight: 500,
                          }}>
                            <div>
                              <div>{partner.name}</div>
                              {partner.website && (
                                <div style={{
                                  fontSize: '0.6875rem',
                                  color: 'var(--color-text-muted)',
                                  marginTop: '2px',
                                }}>
                                  🌐 {partner.website}
                                </div>
                              )}
                            </div>
                          </td>
                          <td style={{
                            padding: 'var(--space-sm) var(--space-md)',
                            color: 'var(--color-text-secondary)',
                          }}>
                            {partner.acronym && (
                              <span style={{
                                padding: '2px 8px',
                                background: 'var(--cgiar-light-gray)',
                                borderRadius: 'var(--radius-sm)',
                                fontSize: '0.6875rem',
                                fontWeight: 500,
                              }}>
                                {partner.acronym}
                              </span>
                            )}
                          </td>
                          <td style={{
                            padding: 'var(--space-sm) var(--space-md)',
                            color: 'var(--color-text-secondary)',
                          }}>
                            {partner.country && <span>📍 {partner.country}</span>}
                          </td>
                          <td style={{
                            padding: 'var(--space-sm) var(--space-md)',
                            textAlign: 'center',
                          }}>
                            <div style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              padding: '4px 10px',
                              background: `${getQualityColor(partner.match_quality)}15`,
                              color: getQualityColor(partner.match_quality),
                              borderRadius: 'var(--radius-sm)',
                              fontSize: '0.75rem',
                              fontWeight: 600,
                            }}>
                              {badge.icon}
                              {badge.label}
                            </div>
                          </td>
                          <td style={{
                            padding: 'var(--space-sm) var(--space-md)',
                            textAlign: 'center',
                          }}>
                            {partner.clarisa_match ? (
                              <button
                                onClick={() => {
                                  setSelectedPartner(partner);
                                  setModalType('clarisa');
                                  setModalOpen(true);
                                }}
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
                                onMouseOver={(e) => e.currentTarget.style.opacity = '0.8'}
                                onMouseOut={(e) => e.currentTarget.style.opacity = '1'}
                              >
                                <Database size={14} />
                                View
                              </button>
                            ) : (
                              <span style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem' }}>—</span>
                            )}
                          </td>
                          <td style={{
                            padding: 'var(--space-sm) var(--space-md)',
                            textAlign: 'center',
                          }}>
                            {partner.top_candidates && partner.top_candidates.length > 0 ? (
                              <button
                                onClick={() => {
                                  setSelectedPartner(partner);
                                  setModalType('candidates');
                                  setModalOpen(true);
                                }}
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
                          <td style={{
                            padding: 'var(--space-sm) var(--space-md)',
                            textAlign: 'center',
                          }}>
                            {partner.web_search ? (
                              <button
                                onClick={() => {
                                  setSelectedPartner(partner);
                                  setModalType('websearch');
                                  setModalOpen(true);
                                }}
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
                                onMouseOver={(e) => e.currentTarget.style.opacity = '0.8'}
                                onMouseOut={(e) => e.currentTarget.style.opacity = '1'}
                              >
                                <Globe size={14} />
                                View
                              </button>
                            ) : (partner.match_quality === 'fair' || partner.match_quality === 'good') ? (
                              <button
                                onClick={() => handleManualWebSearch(partner)}
                                disabled={runningWebSearch[partner.id]}
                                style={{
                                  padding: '6px 12px',
                                  background: runningWebSearch[partner.id] 
                                    ? 'var(--cgiar-gray)' 
                                    : 'rgba(252, 211, 77, 0.3)',
                                  color: runningWebSearch[partner.id] 
                                    ? 'white' 
                                    : 'var(--cgiar-navy)',
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
                                onMouseOver={(e) => !runningWebSearch[partner.id] && (e.currentTarget.style.background = 'rgba(252, 211, 77, 0.5)')}
                                onMouseOut={(e) => !runningWebSearch[partner.id] && (e.currentTarget.style.background = 'rgba(252, 211, 77, 0.3)')}
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
                          <td style={{
                            padding: 'var(--space-sm) var(--space-md)',
                            textAlign: 'center',
                          }}>
                            {partner.api_data ? (
                              <div style={{
                                display: 'flex',
                                gap: '8px',
                                justifyContent: 'center',
                                alignItems: 'center',
                              }}>
                                <button
                                  onClick={() => {
                                    setSelectedPartner(partner);
                                    setModalType('accept');
                                    setModalOpen(true);
                                  }}
                                  disabled={respondingToRequest}
                                  style={{
                                    padding: '6px 10px',
                                    background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                                    color: 'white',
                                    borderRadius: 'var(--radius-sm)',
                                    border: 'none',
                                    cursor: respondingToRequest ? 'not-allowed' : 'pointer',
                                    fontSize: '0.75rem',
                                    fontWeight: 500,
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '4px',
                                    transition: 'all 0.2s',
                                    opacity: respondingToRequest ? 0.5 : 1,
                                  }}
                                  onMouseOver={(e) => !respondingToRequest && (e.currentTarget.style.opacity = '0.85')}
                                  onMouseOut={(e) => !respondingToRequest && (e.currentTarget.style.opacity = '1')}
                                  title="Accept this partner request"
                                >
                                  <ThumbsUp size={14} />
                                  Accept
                                </button>
                                <button
                                  onClick={() => {
                                    setSelectedPartner(partner);
                                    setModalType('reject');
                                    setRejectJustification('');
                                    setModalOpen(true);
                                  }}
                                  disabled={respondingToRequest}
                                  style={{
                                    padding: '6px 10px',
                                    background: 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)',
                                    color: 'white',
                                    borderRadius: 'var(--radius-sm)',
                                    border: 'none',
                                    cursor: respondingToRequest ? 'not-allowed' : 'pointer',
                                    fontSize: '0.75rem',
                                    fontWeight: 500,
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '4px',
                                    transition: 'all 0.2s',
                                    opacity: respondingToRequest ? 0.5 : 1,
                                  }}
                                  onMouseOver={(e) => !respondingToRequest && (e.currentTarget.style.opacity = '0.85')}
                                  onMouseOut={(e) => !respondingToRequest && (e.currentTarget.style.opacity = '1')}
                                  title="Reject this partner request"
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
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </motion.div>
        )}
      </main>

      {/* Modal */}
      <AnimatePresence>
        {modalOpen && selectedPartner && (
          <>
            {/* Overlay */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setModalOpen(false)}
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
                  background: modalType === 'clarisa' ? 'var(--cgiar-blue)' : modalType === 'candidates' ? 'linear-gradient(135deg, #8B5CF6 0%, #6D28D9 100%)' : modalType === 'accept' ? 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)' : modalType === 'reject' ? 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)' : 'var(--cgiar-yellow)',
                  borderTopLeftRadius: 'var(--radius-lg)',
                  borderTopRightRadius: 'var(--radius-lg)',
                }}>
                  <div>
                    <h3 style={{
                      color: modalType === 'candidates' || modalType === 'clarisa' || modalType === 'accept' || modalType === 'reject' ? 'white' : 'var(--cgiar-navy)',
                      fontSize: '1.125rem',
                      fontWeight: 600,
                      marginBottom: '4px',
                    }}>
                      {selectedPartner.name}
                    </h3>
                    <p style={{
                      color: modalType === 'candidates' || modalType === 'clarisa' || modalType === 'accept' || modalType === 'reject' ? 'rgba(255,255,255,0.9)' : 'var(--color-text-secondary)',
                      fontSize: '0.875rem',
                    }}>
                      {modalType === 'clarisa' ? 'CLARISA Match Details' : modalType === 'candidates' ? 'Top Candidate Matches' : modalType === 'accept' ? 'Accept Partner Request' : modalType === 'reject' ? 'Reject Partner Request' : 'Web Search Results'}
                    </p>
                  </div>
                  <button
                    onClick={() => setModalOpen(false)}
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      color: modalType === 'candidates' || modalType === 'clarisa' || modalType === 'accept' || modalType === 'reject' ? 'white' : 'var(--cgiar-navy)',
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
                  {modalType === 'clarisa' && selectedPartner.clarisa_match && (
                    <div>
                      <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                        gap: 'var(--space-md)',
                        marginBottom: 'var(--space-lg)',
                      }}>
                        <DataField label="Institution" value={selectedPartner.clarisa_match.name} />
                        <DataField label="CLARISA ID" value={selectedPartner.clarisa_match.clarisa_id} />
                        {selectedPartner.clarisa_match.acronym && (
                          <DataField label="Acronym" value={selectedPartner.clarisa_match.acronym} />
                        )}
                        {selectedPartner.clarisa_match.institution_type && (
                          <DataField label="Type" value={selectedPartner.clarisa_match.institution_type} />
                        )}
                        {selectedPartner.clarisa_match.countries.length > 0 && (
                          <DataField
                            label="Countries"
                            value={selectedPartner.clarisa_match.countries.join(', ')}
                            fullWidth
                          />
                        )}
                        {selectedPartner.clarisa_match.website && (
                          <DataField
                            label="Website"
                            value={selectedPartner.clarisa_match.website}
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
                            value={selectedPartner.clarisa_match.scores.final_score}
                          />
                          <ScoreBar
                            label="Similarity"
                            value={selectedPartner.clarisa_match.scores.cosine_similarity}
                          />
                          <ScoreBar
                            label="Name Match"
                            value={selectedPartner.clarisa_match.scores.fuzz_name_score}
                          />
                          <ScoreBar
                            label="Acronym Match"
                            value={selectedPartner.clarisa_match.scores.fuzz_acronym_score}
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {modalType === 'websearch' && selectedPartner.web_search && (
                    <div>
                      {selectedPartner.web_search.success ? (
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
                            {selectedPartner.web_search.result || ''}
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
                          ⚠️ {selectedPartner.web_search.error}
                        </div>
                      )}
                    </div>
                  )}

                  {modalType === 'candidates' && selectedPartner.top_candidates && (
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
                          <strong>ℹ️ Information:</strong> These are the top {selectedPartner.top_candidates.length} candidate matches from the CLARISA database, ranked by relevance score. {selectedPartner.match_found ? 'The first candidate exceeded the match threshold and was selected as the primary match.' : 'None of these candidates exceeded the match threshold, but they represent the closest matches found.'}
                        </p>
                      </div>

                      <div style={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 'var(--space-md)',
                      }}>
                        {selectedPartner.top_candidates.map((candidate, idx) => (
                          <motion.div
                            key={idx}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: idx * 0.05 }}
                            style={{
                              background: 'white',
                              border: idx === 0 && selectedPartner.match_found ? '2px solid var(--cgiar-green)' : '1px solid var(--cgiar-gray)',
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
                              background: idx === 0 && selectedPartner.match_found ? 'var(--cgiar-green)' : 'linear-gradient(135deg, #8B5CF6 0%, #6D28D9 100%)',
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
                              {idx === 0 && selectedPartner.match_found && <CheckCircle2 size={12} />}
                              #{idx + 1} {idx === 0 && selectedPartner.match_found && 'SELECTED'}
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
                  {modalType === 'accept' && selectedPartner && (
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
                              onClick={() => setModalOpen(false)}
                              disabled={respondingToRequest}
                              style={{
                                padding: '10px 20px',
                                background: 'white',
                                color: 'var(--cgiar-navy)',
                                border: '2px solid var(--cgiar-gray)',
                                borderRadius: 'var(--radius-md)',
                                cursor: respondingToRequest ? 'not-allowed' : 'pointer',
                                fontSize: '0.875rem',
                                fontWeight: 500,
                                transition: 'all 0.2s',
                                opacity: respondingToRequest ? 0.5 : 1,
                              }}
                              onMouseOver={(e) => !respondingToRequest && (e.currentTarget.style.borderColor = 'var(--color-text-muted)')}
                              onMouseOut={(e) => !respondingToRequest && (e.currentTarget.style.borderColor = 'var(--cgiar-gray)')}
                            >
                              Cancel
                            </button>
                            <button
                              onClick={() => selectedPartner && handleAcceptRequest()}
                              disabled={respondingToRequest}
                              style={{
                                padding: '10px 20px',
                                background: respondingToRequest ? 'var(--cgiar-gray)' : 'var(--cgiar-green)',
                                color: 'white',
                                border: 'none',
                                borderRadius: 'var(--radius-md)',
                                cursor: respondingToRequest ? 'not-allowed' : 'pointer',
                                fontSize: '0.875rem',
                                fontWeight: 600,
                                transition: 'all 0.2s',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '6px',
                              }}
                              onMouseOver={(e) => {
                                if (!respondingToRequest) {
                                  e.currentTarget.style.background = '#059669';
                                  e.currentTarget.style.transform = 'translateY(-1px)';
                                  e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                                }
                              }}
                              onMouseOut={(e) => {
                                if (!respondingToRequest) {
                                  e.currentTarget.style.background = 'var(--cgiar-green)';
                                  e.currentTarget.style.transform = 'translateY(0)';
                                  e.currentTarget.style.boxShadow = 'none';
                                }
                              }}
                            >
                              {respondingToRequest ? (
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
                  {modalType === 'reject' && selectedPartner && (
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
                              onChange={(e) => setRejectJustification(e.target.value)}
                              placeholder="Provide any details about why this request is being rejected..."
                              disabled={respondingToRequest}
                              style={{
                                width: '100%',
                                minHeight: '120px',
                                padding: 'var(--space-sm)',
                                border: '1px solid var(--cgiar-gray)',
                                borderRadius: 'var(--radius-sm)',
                                fontSize: '0.875rem',
                                fontFamily: 'inherit',
                                resize: 'vertical',
                                background: respondingToRequest ? '#F3F4F6' : 'white',
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
                                setModalOpen(false);
                                setRejectJustification('');
                              }}
                              disabled={respondingToRequest}
                              style={{
                                padding: '10px 20px',
                                background: 'white',
                                color: 'var(--cgiar-navy)',
                                border: '1px solid var(--cgiar-gray)',
                                borderRadius: 'var(--radius-sm)',
                                cursor: respondingToRequest ? 'not-allowed' : 'pointer',
                                fontSize: '0.875rem',
                                fontWeight: 500,
                                transition: 'all 0.2s',
                                opacity: respondingToRequest ? 0.5 : 1,
                              }}
                            >
                              Cancel
                            </button>
                            <button
                              onClick={() => selectedPartner && handleRejectRequest()}
                              disabled={respondingToRequest}
                              style={{
                                padding: '10px 20px',
                                background: 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)',
                                color: 'white',
                                border: 'none',
                                borderRadius: 'var(--radius-sm)',
                                cursor: respondingToRequest ? 'not-allowed' : 'pointer',
                                fontSize: '0.875rem',
                                fontWeight: 600,
                                transition: 'all 0.2s',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '6px',
                                opacity: respondingToRequest ? 0.5 : 1,
                              }}
                            >
                              {respondingToRequest ? (
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

      <style jsx>{`
        .spinner {
          width: 20px;
          height: 20px;
          border: 3px solid rgba(255,255,255,0.3);
          border-top-color: white;
          border-radius: 50%;
          animation: spin 0.6s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

// Statistics Card Component
function StatCard({ title, value, percentage, subtitle, color, icon }: {
  title: string;
  value: number;
  percentage?: number;
  subtitle?: string;
  color: string;
  icon: React.ReactNode;
}) {
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
          <p style={{
            color: 'var(--color-text-muted)',
            fontSize: '0.75rem',
            fontWeight: 500,
            marginBottom: '4px',
          }}>
            {title}
          </p>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
            <h3 style={{
              fontSize: '1.75rem',
              fontWeight: 700,
              color,
              lineHeight: 1,
            }}>
              {value}
            </h3>
            {percentage !== undefined && (
              <span style={{
                color: 'var(--color-text-muted)',
                fontSize: '0.875rem',
                fontWeight: 500,
              }}>
                ({percentage}%)
              </span>
            )}
          </div>
          {subtitle && (
            <p style={{ fontSize: '0.6875rem', color: 'var(--color-text-muted)', marginTop: '2px' }}>
              {subtitle}
            </p>
          )}
        </div>
        <div style={{
          width: '36px',
          height: '36px',
          background: `${color}15`,
          borderRadius: 'var(--radius-sm)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color,
        }}>
          {icon}
        </div>
      </div>
    </motion.div>
  );
}

// Partner Card Component
function PartnerCard({ partner, index, expanded, onToggle, getQualityColor, getQualityBadge }: {
  partner: Partner;
  index: number;
  expanded: boolean;
  onToggle: () => void;
  getQualityColor: (quality: string) => string;
  getQualityBadge: (quality: string) => { label: string; icon: React.ReactNode };
}) {
  const badge = getQualityBadge(partner.match_quality);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.03 }}
      style={{
        background: 'white',
        borderRadius: 'var(--radius-md)',
        boxShadow: expanded ? 'var(--shadow-lg)' : 'var(--shadow-sm)',
        border: '1px solid var(--cgiar-gray)',
        overflow: 'hidden',
        transition: 'all 0.3s ease',
      }}
    >
      {/* Card Header - Always Visible */}
      <div
        onClick={onToggle}
        style={{
          padding: 'var(--space-md)',
          cursor: 'pointer',
          borderLeft: `3px solid ${getQualityColor(partner.match_quality)}`,
          background: expanded ? '#FAFBFC' : 'white',
          transition: 'background 0.2s',
        }}
      >
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'start',
          gap: 'var(--space-md)',
        }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)', marginBottom: '4px' }}>
              <h3 style={{
                fontSize: '1rem',
                fontWeight: 600,
                color: 'var(--cgiar-navy)',
              }}>
                {partner.name}
              </h3>
              {partner.acronym && (
                <span style={{
                  padding: '2px 8px',
                  background: 'var(--cgiar-light-gray)',
                  color: 'var(--color-text-secondary)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.6875rem',
                  fontWeight: 500,
                }}>
                  {partner.acronym}
                </span>
              )}
            </div>
            {(partner.country || partner.website) && (
              <div style={{
                display: 'flex',
                gap: 'var(--space-sm)',
                fontSize: '0.75rem',
                color: 'var(--color-text-muted)',
              }}>
                {partner.country && <span>📍 {partner.country}</span>}
                {partner.website && <span>🌐 {partner.website}</span>}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)' }}>
            <div style={{
              padding: '4px 10px',
              background: `${getQualityColor(partner.match_quality)}15`,
              color: getQualityColor(partner.match_quality),
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.75rem',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}>
              {badge.icon}
              {badge.label}
            </div>
            {expanded ? <ChevronUp size={18} color="var(--color-text-muted)" /> : <ChevronDown size={18} color="var(--color-text-muted)" />}
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{
              padding: 'var(--space-md)',
              borderTop: '1px solid var(--cgiar-gray)',
              background: '#FAFBFC',
            }}>
              {/* CLARISA Match Section */}
              {partner.clarisa_match && (
                <div style={{
                  background: 'white',
                  padding: 'var(--space-md)',
                  borderRadius: 'var(--radius-sm)',
                  marginBottom: 'var(--space-sm)',
                  border: '1px solid var(--cgiar-gray)',
                }}>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-xs)',
                    marginBottom: 'var(--space-sm)',
                  }}>
                    <div style={{
                      width: '28px',
                      height: '28px',
                      background: 'var(--cgiar-blue)',
                      borderRadius: 'var(--radius-sm)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}>
                      <Database size={16} color="white" />
                    </div>
                    <h4 style={{
                      fontSize: '0.875rem',
                      fontWeight: 600,
                      color: 'var(--cgiar-navy)',
                    }}>
                      CLARISA Match
                    </h4>
                  </div>

                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                    gap: 'var(--space-sm)',
                    marginBottom: 'var(--space-sm)',
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

                  {/* Scores */}
                  <div style={{
                    padding: 'var(--space-md)',
                    background: '#F0F9E8',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid #D4EAC3',
                  }}>
                    <p style={{
                      fontSize: '0.875rem',
                      fontWeight: 600,
                      color: 'var(--cgiar-navy)',
                      marginBottom: 'var(--space-sm)',
                    }}>
                      Match Confidence Scores
                    </p>
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
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
                        label="Acronym"
                        value={partner.clarisa_match.scores.fuzz_acronym_score}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Web Search Section */}
              {partner.web_search && (
                <div style={{
                  background: 'white',
                  padding: 'var(--space-md)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--cgiar-gray)',
                }}>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-xs)',
                    marginBottom: 'var(--space-sm)',
                  }}>
                    <div style={{
                      width: '28px',
                      height: '28px',
                      background: 'var(--cgiar-yellow)',
                      borderRadius: 'var(--radius-sm)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}>
                      <Globe size={16} color="var(--cgiar-navy)" />
                    </div>
                    <h4 style={{
                      fontSize: '0.875rem',
                      fontWeight: 600,
                      color: 'var(--cgiar-navy)',
                    }}>
                      Web Search Results
                    </h4>
                  </div>

                  {partner.web_search.success ? (
                    <div className="markdown-content" style={{
                      background: '#FAFBFC',
                      padding: 'var(--space-sm)',
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

              {/* No Match Message */}
              {!partner.match_found && !partner.web_search && (
                <div style={{
                  padding: 'var(--space-xl)',
                  textAlign: 'center',
                  background: 'white',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--cgiar-gray)',
                }}>
                  <XCircle size={48} color="var(--color-no-match)" style={{ margin: '0 auto var(--space-md)' }} />
                  <p style={{
                    fontSize: '1rem',
                    color: 'var(--color-text-secondary)',
                    fontWeight: 500,
                  }}>
                    No match found in CLARISA database
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// Helper Components
function DataField({ label, value, fullWidth }: { label: string; value: string; fullWidth?: boolean }) {
  return (
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
}

function ScoreBar({ label, value }: { label: string; value: number }) {
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
}
