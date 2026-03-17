'use client';

import { useState } from 'react';

export const useFileUpload = () => {
  const [file, setFile] = useState<File | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      return e.target.files[0];
    }
    return null;
  };

  const clearFile = () => {
    setFile(null);
  };

  return {
    file,
    setFile,
    handleFileChange,
    clearFile,
  };
};
