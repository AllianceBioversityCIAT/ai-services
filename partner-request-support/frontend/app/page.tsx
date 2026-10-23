'use client';

import { useEffect, useState } from 'react';
import { LoginPage } from './components/LoginPage';
import { Header } from './components/Header';
import { AIDisclaimer } from './components/AIDisclaimer';
import { UploadSection } from './components/UploadSection';
import { ResultsSection } from './components/ResultsSection';
import { Modal } from './components/ModalDialog';
import { useAuth, usePartnerProcessing, useApiSync, useFileUpload, useModal, useWebSearch } from './hooks';
import { Partner } from './types';
import { partnerService } from './services';

export default function Home() {
  const {
    isAuthenticated,
    authUser,
    authToken,
    loginError,
    isLoading: authLoading,
    login,
    logout,
  } = useAuth();

  const {
    processing,
    results,
    message,
    error,
    processExcelFile,
    processApiPartners,
    clearResults,
    clearError,
    setResults,
  } = usePartnerProcessing();

  const { apiPartners, batchSize, syncing, syncError, syncPartnerRequests } = useApiSync();
  
  const { file, handleFileChange, clearFile } = useFileUpload();
  
  const { modalOpen, modalType, selectedPartner, openModal, closeModal } = useModal();
  
  const { runningWebSearch, runManualWebSearch } = useWebSearch(results, setResults);

  const [respondingToRequest, setRespondingToRequest] = useState(false);
  const [responseMessage, setResponseMessage] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  const [rejectJustification, setRejectJustification] = useState('');

  // Sync partner requests on component mount (only if authenticated)
  useEffect(() => {
    if (isAuthenticated) {
      syncPartnerRequests();
    }
  }, [isAuthenticated]);

  const handleLogin = async (email: string, password: string) => {
    const success = await login({ email, password });
    return success;
  };

  const handleLogout = () => {
    logout();
    clearResults();
    clearFile();
  };

  const handleUpload = () => {
    if (!file || !authToken || !authUser) return;
    processExcelFile(file, authUser.email, authUser.name, authToken);
  };

  const handleProcessApiPartners = () => {
    processApiPartners();
  };

  const handleNewUpload = () => {
    // Requests answered in CLARISA are no longer pending, so re-sync to show the
    // shrunken queue and the next batch. Excel runs never touch that queue.
    const cameFromApiQueue = results?.partners?.some((partner) => partner.api_data) ?? false;

    clearResults();
    clearFile();

    if (cameFromApiQueue) {
      syncPartnerRequests();
    }
  };

  const handleClearCache = async () => {
    await partnerService.clearCache();
  };

  // Modal handlers
  const handleViewClarisa = (partner: Partner) => {
    openModal('clarisa', partner);
  };

  const handleViewCandidates = (partner: Partner) => {
    openModal('candidates', partner);
  };

  const handleViewWebSearch = (partner: Partner) => {
    openModal('websearch', partner);
  };

  const handleRunWebSearch = async (partner: Partner) => {
    try {
      const updatedPartner = await runManualWebSearch(partner);
      if (updatedPartner?.web_search?.success) {
        // Auto-open modal if successful
        handleViewWebSearch(updatedPartner);
      }
    } catch (err) {
      console.error('Web search error:', err);
    }
  };

  const handleAccept = (partner: Partner) => {
    openModal('accept', partner);
  };

  const handleReject = (partner: Partner) => {
    openModal('reject', partner);
  };

  const handleConfirmAccept = async () => {
    if (!selectedPartner?.api_data?.request_id || !authToken || !authUser) {
      setResponseMessage({ type: 'error', message: 'No request ID available' });
      return;
    }

    setRespondingToRequest(true);
    setResponseMessage(null);

    try {
      await partnerService.respondToRequest(
        selectedPartner.api_data.request_id,
        authUser.id,
        true,
        authToken
      );

      setResponseMessage({ 
        type: 'success', 
        message: `Partner request for "${selectedPartner.name}" successfully accepted!` 
      });

      // Remove from results
      if (results) {
        const updatedPartners = results.partners.filter(
          (p) => p.api_data?.request_id !== selectedPartner.api_data?.request_id
        );
        setResults({
          ...results,
          partners: updatedPartners,
          stats: {
            ...results.stats,
            total: updatedPartners.length,
          },
        });
      }

      // Close modal after short delay
      setTimeout(() => {
        closeModal();
        setResponseMessage(null);
      }, 2000);

    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Error accepting partner request';
      setResponseMessage({ type: 'error', message: errorMsg });
    } finally {
      setRespondingToRequest(false);
    }
  };

  const handleConfirmReject = async () => {
    if (!selectedPartner?.api_data?.request_id || !authToken || !authUser) {
      setResponseMessage({ type: 'error', message: 'No request ID available' });
      return;
    }

    setRespondingToRequest(true);
    setResponseMessage(null);

    try {
      await partnerService.respondToRequest(
        selectedPartner.api_data.request_id,
        authUser.id,
        false,
        authToken,
        rejectJustification.trim() || 'No justification provided'
      );

      setResponseMessage({ 
        type: 'success', 
        message: `Partner request for "${selectedPartner.name}" successfully rejected.` 
      });

      // Remove from results
      if (results) {
        const updatedPartners = results.partners.filter(
          (p) => p.api_data?.request_id !== selectedPartner.api_data?.request_id
        );
        setResults({
          ...results,
          partners: updatedPartners,
          stats: {
            ...results.stats,
            total: updatedPartners.length,
          },
        });
      }

      // Close modal after short delay
      setTimeout(() => {
        closeModal();
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

  // Show login screen if not authenticated
  if (!isAuthenticated) {
    return <LoginPage onLogin={handleLogin} loginError={loginError} isLoading={authLoading} />;
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--color-background)' }}>
      <Header authUser={authUser} onLogout={handleLogout} />

      <main
        style={{
          maxWidth: '1400px',
          margin: '0 auto',
          padding: 'var(--space-lg) var(--space-lg)',
        }}
      >
        <AIDisclaimer />

        {/* Upload Section */}
        {!results && (
          <UploadSection
            file={file}
            onFileChange={handleFileChange}
            processing={processing}
            message={message}
            error={error}
            onUpload={handleUpload}
            apiPartners={apiPartners}
            batchSize={batchSize}
            syncing={syncing}
            syncError={syncError}
            onSyncPartnerRequests={syncPartnerRequests}
            onProcessApiPartners={handleProcessApiPartners}
            onClearCache={handleClearCache}
          />
        )}

        {/* Results Section */}
        {results && (
          <ResultsSection
            results={results}
            runningWebSearch={runningWebSearch}
            onViewClarisa={handleViewClarisa}
            onViewCandidates={handleViewCandidates}
            onViewWebSearch={handleViewWebSearch}
            onRunWebSearch={handleRunWebSearch}
            onAccept={handleAccept}
            onReject={handleReject}
            respondingToRequest={respondingToRequest}
            onNewUpload={handleNewUpload}
          />
        )}

        {/* Modal */}
        <Modal
          isOpen={modalOpen}
          type={modalType}
          partner={selectedPartner}
          onClose={closeModal}
          onAccept={handleConfirmAccept}
          onReject={setRejectJustification}
          onConfirmReject={handleConfirmReject}
          rejectJustification={rejectJustification}
          responseMessage={responseMessage}
          isResponding={respondingToRequest}
        />
      </main>
    </div>
  );
}
