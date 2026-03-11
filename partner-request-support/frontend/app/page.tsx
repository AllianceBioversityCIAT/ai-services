'use client';

import { useState, useEffect } from 'react';
import { Upload, FileSpreadsheet, CheckCircle2, XCircle, Globe, Database, BarChart3, Search, ChevronDown, ChevronUp, Info, RefreshCw, Cloud } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';

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

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [processing, setProcessing] = useState(false);
  const [results, setResults] = useState<ProcessingResults | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedPartner, setExpandedPartner] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [modalType, setModalType] = useState<'clarisa' | 'websearch' | 'candidates' | null>(null);
  const [selectedPartner, setSelectedPartner] = useState<Partner | null>(null);
  const [showQualityInfo, setShowQualityInfo] = useState(false);
  const [uploadMode, setUploadMode] = useState<'excel' | 'api'>('excel');
  const [apiPartners, setApiPartners] = useState<ApiPartnerRequest[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);

  // Sync partner requests on component mount
  useEffect(() => {
    syncPartnerRequests();
  }, []);

  const syncPartnerRequests = async () => {
    setSyncing(true);
    setSyncError(null);
    
    try {
      const response = await axios.get('http://localhost:8000/api/sync-partner-requests');
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

    try {
      const response = await axios.post<ProcessingResults>(
        'http://localhost:8000/api/process-api-partners',
        null,  // Will process first 5 by default
        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      setResults(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error processing API partners. Please try again.');
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

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file first');
      return;
    }

    setProcessing(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post<ProcessingResults>(
        'http://localhost:8000/api/process-partners',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      setResults(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error processing file. Please try again.');
    } finally {
      setProcessing(false);
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
  );

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
                        Processing...
                      </>
                    ) : (
                      <>
                        <BarChart3 size={18} />
                        Analyze Partners
                      </>
                    )}
                  </button>

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
                    }}>
                      <li><strong>Column 1:</strong> Partner Name (required)</li>
                      <li><strong>Column 2:</strong> Acronym (optional)</li>
                      <li><strong>Column 3:</strong> Website (optional)</li>
                      <li><strong>Column 5:</strong> Country (optional)</li>
                    </ul>
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
                        Processing...
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
                    setExpandedPartner(null);
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
                  background: modalType === 'clarisa' ? 'var(--cgiar-blue)' : modalType === 'candidates' ? 'linear-gradient(135deg, #8B5CF6 0%, #6D28D9 100%)' : 'var(--cgiar-yellow)',
                  borderTopLeftRadius: 'var(--radius-lg)',
                  borderTopRightRadius: 'var(--radius-lg)',
                }}>
                  <div>
                    <h3 style={{
                      color: modalType === 'candidates' || modalType === 'clarisa' ? 'white' : 'var(--cgiar-navy)',
                      fontSize: '1.125rem',
                      fontWeight: 600,
                      marginBottom: '4px',
                    }}>
                      {selectedPartner.name}
                    </h3>
                    <p style={{
                      color: modalType === 'candidates' || modalType === 'clarisa' ? 'rgba(255,255,255,0.9)' : 'var(--color-text-secondary)',
                      fontSize: '0.875rem',
                    }}>
                      {modalType === 'clarisa' ? 'CLARISA Match Details' : modalType === 'candidates' ? 'Top Candidate Matches' : 'Web Search Results'}
                    </p>
                  </div>
                  <button
                    onClick={() => setModalOpen(false)}
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      color: modalType === 'candidates' || modalType === 'clarisa' ? 'white' : 'var(--cgiar-navy)',
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
