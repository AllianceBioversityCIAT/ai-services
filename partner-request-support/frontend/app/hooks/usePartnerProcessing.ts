'use client';

import { useState } from 'react';
import { partnerService } from '../services/partnerService';
import { ProcessingResults } from '../types/api.types';

export const usePartnerProcessing = () => {
  const [processing, setProcessing] = useState(false);
  const [results, setResults] = useState<ProcessingResults | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState<string | null>(null);

  const processExcelFile = async (
    file: File,
    userEmail: string,
    userName: string,
    authToken: string
  ) => {
    setProcessing(true);
    setError(null);
    setMessage('Synchronizing CLARISA database...');

    try {
      const data = await partnerService.processExcelFile(file, userEmail, userName, authToken);
      setResults(data);
      setMessage('');
      return data;
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Error processing file. Please try again.';
      setError(errorMsg);
      setMessage('');
      throw err;
    } finally {
      setProcessing(false);
    }
  };

  const processApiPartners = async () => {
    setProcessing(true);
    setError(null);
    setMessage('Synchronizing CLARISA database...');

    try {
      const data = await partnerService.processApiPartners();
      setResults(data);
      setMessage('');
      return data;
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Error processing API partners. Please try again.';
      setError(errorMsg);
      setMessage('');
      throw err;
    } finally {
      setProcessing(false);
    }
  };

  const clearResults = () => {
    setResults(null);
    setError(null);
    setMessage('');
  };

  return {
    processing,
    results,
    message,
    error,
    processExcelFile,
    processApiPartners,
    clearResults,
    setResults,
  };
};
