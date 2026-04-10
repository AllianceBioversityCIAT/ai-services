'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import * as XLSX from 'xlsx';
import { FileSpreadsheet, X, Play, Table2, Rows3, Columns3 } from 'lucide-react';

interface ExcelPreviewModalProps {
  isOpen: boolean;
  file: File | null;
  onClose: () => void;
  onContinue: () => void;
}

interface ParsedExcel {
  headers: string[];
  rows: (string | number | boolean | null)[][];
  totalRows: number;
  totalCols: number;
}

const PREVIEW_ROWS = 6;

export const ExcelPreviewModal = ({
  isOpen,
  file,
  onClose,
  onContinue,
}: ExcelPreviewModalProps) => {
  const [parsed, setParsed] = useState<ParsedExcel | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen || !file) {
      setParsed(null);
      setParseError(null);
      return;
    }

    setLoading(true);
    setParseError(null);

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target?.result as ArrayBuffer);
        const workbook = XLSX.read(data, { type: 'array' });
        const sheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[sheetName];
        const jsonData = XLSX.utils.sheet_to_json<(string | number | boolean | null)[]>(
          worksheet,
          { header: 1, defval: '' }
        );

        if (jsonData.length === 0) {
          setParseError('The Excel file appears to be empty.');
          setLoading(false);
          return;
        }

        const headers = (jsonData[0] as (string | number | boolean | null)[]).map((h) =>
          h !== null && h !== undefined ? String(h) : ''
        );
        const dataRows = jsonData.slice(1) as (string | number | boolean | null)[][];

        setParsed({
          headers,
          rows: dataRows,
          totalRows: dataRows.length,
          totalCols: headers.length,
        });
      } catch {
        setParseError('Could not read the Excel file. Make sure it is a valid .xlsx or .xls file.');
      } finally {
        setLoading(false);
      }
    };
    reader.onerror = () => {
      setParseError('Error reading the file.');
      setLoading(false);
    };
    reader.readAsArrayBuffer(file);
  }, [isOpen, file]);

  if (!isOpen) return null;

  const previewRows = parsed ? parsed.rows.slice(0, PREVIEW_ROWS) : [];

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.55)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: 'var(--space-md)',
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) onClose();
          }}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 12 }}
            transition={{ duration: 0.22 }}
            style={{
              background: 'white',
              borderRadius: 'var(--radius-xl)',
              boxShadow: 'var(--shadow-lg)',
              width: '100%',
              maxWidth: '860px',
              maxHeight: '90vh',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
            }}
          >
            {/* Header */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: 'var(--space-md)',
                borderBottom: '1px solid var(--cgiar-light-gray)',
                flexShrink: 0,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: 'var(--radius-md)',
                    background: 'linear-gradient(135deg, var(--cgiar-green), #629600)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <FileSpreadsheet size={18} color="white" />
                </div>
                <div>
                  <h2
                    style={{
                      fontSize: '1rem',
                      fontWeight: 700,
                      color: 'var(--cgiar-navy)',
                      margin: 0,
                    }}
                  >
                    Excel Validation
                  </h2>
                  <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', margin: 0 }}>
                    {file?.name}
                  </p>
                </div>
              </div>
              <button
                onClick={onClose}
                style={{
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '4px',
                  borderRadius: 'var(--radius-sm)',
                  color: 'var(--color-text-muted)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Body */}
            <div style={{ flex: 1, overflow: 'auto', padding: 'var(--space-md)' }}>
              {loading && (
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 'var(--space-sm)',
                    padding: 'var(--space-xl)',
                  }}
                >
                  <div className="spinner" />
                  <p style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>
                    Reading file…
                  </p>
                </div>
              )}

              {parseError && (
                <div
                  style={{
                    padding: 'var(--space-md)',
                    background: '#FEF2F2',
                    borderRadius: 'var(--radius-md)',
                    borderLeft: '3px solid #DC2626',
                    color: '#991B1B',
                    fontSize: '0.875rem',
                  }}
                >
                  {parseError}
                </div>
              )}

              {parsed && !loading && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  {/* Stats row */}
                  <div
                    style={{
                      display: 'flex',
                      gap: 'var(--space-sm)',
                      marginBottom: 'var(--space-md)',
                    }}
                  >
                    {[
                      {
                        icon: <Rows3 size={16} color="var(--cgiar-green)" />,
                        label: 'Rows to process',
                        value: parsed.totalRows,
                      },
                      {
                        icon: <Columns3 size={16} color="var(--cgiar-blue)" />,
                        label: 'Columns detected',
                        value: parsed.totalCols,
                      },
                      {
                        icon: <Table2 size={16} color="var(--cgiar-navy)" />,
                        label: 'Preview shown',
                        value: `${Math.min(previewRows.length, PREVIEW_ROWS)} of ${parsed.totalRows}`,
                      },
                    ].map((stat) => (
                      <div
                        key={stat.label}
                        style={{
                          flex: 1,
                          background: 'var(--cgiar-light-gray)',
                          borderRadius: 'var(--radius-md)',
                          padding: 'var(--space-sm)',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 'var(--space-xs)',
                        }}
                      >
                        {stat.icon}
                        <div>
                          <p
                            style={{
                              fontSize: '1.1rem',
                              fontWeight: 700,
                              color: 'var(--cgiar-navy)',
                              margin: 0,
                              lineHeight: 1,
                            }}
                          >
                            {stat.value}
                          </p>
                          <p
                            style={{
                              fontSize: '0.7rem',
                              color: 'var(--color-text-muted)',
                              margin: 0,
                            }}
                          >
                            {stat.label}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Table preview */}
                  <div
                    style={{
                      overflow: 'auto',
                      border: '1px solid var(--cgiar-light-gray)',
                      borderRadius: 'var(--radius-md)',
                    }}
                  >
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
                            background: 'var(--cgiar-navy)',
                            color: 'white',
                          }}
                        >
                          <th
                            style={{
                              padding: '8px 10px',
                              textAlign: 'center',
                              fontWeight: 600,
                              fontSize: '0.7rem',
                              whiteSpace: 'nowrap',
                              width: 36,
                              opacity: 0.7,
                            }}
                          >
                            #
                          </th>
                          {parsed.headers.map((header, i) => (
                            <th
                              key={i}
                              style={{
                                padding: '8px 10px',
                                textAlign: 'left',
                                fontWeight: 600,
                                fontSize: '0.75rem',
                                whiteSpace: 'nowrap',
                              }}
                            >
                              {header || `Col ${i}`}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {previewRows.map((row, rowIdx) => (
                          <tr
                            key={rowIdx}
                            style={{
                              background: rowIdx % 2 === 0 ? 'white' : '#F8FAFC',
                            }}
                          >
                            <td
                              style={{
                                padding: '7px 10px',
                                textAlign: 'center',
                                color: 'var(--color-text-muted)',
                                fontSize: '0.7rem',
                                borderTop: '1px solid var(--cgiar-light-gray)',
                              }}
                            >
                              {rowIdx + 1}
                            </td>
                            {parsed.headers.map((_, colIdx) => (
                              <td
                                key={colIdx}
                                style={{
                                  padding: '7px 10px',
                                  color: 'var(--cgiar-navy)',
                                  borderTop: '1px solid var(--cgiar-light-gray)',
                                  maxWidth: 200,
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap',
                                }}
                                title={String(row[colIdx] ?? '')}
                              >
                                {row[colIdx] !== null && row[colIdx] !== undefined
                                  ? String(row[colIdx])
                                  : ''}
                              </td>
                            ))}
                          </tr>
                        ))}
                        {parsed.totalRows > PREVIEW_ROWS && (
                          <tr>
                            <td
                              colSpan={parsed.headers.length + 1}
                              style={{
                                padding: '8px 10px',
                                textAlign: 'center',
                                color: 'var(--color-text-muted)',
                                fontSize: '0.75rem',
                                fontStyle: 'italic',
                                borderTop: '1px solid var(--cgiar-light-gray)',
                                background: '#F8FAFC',
                              }}
                            >
                              + {parsed.totalRows - PREVIEW_ROWS} more rows not shown
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </motion.div>
              )}
            </div>

            {/* Footer */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'flex-end',
                gap: 'var(--space-sm)',
                padding: 'var(--space-md)',
                borderTop: '1px solid var(--cgiar-light-gray)',
                flexShrink: 0,
              }}
            >
              <button
                onClick={onClose}
                style={{
                  padding: '8px 20px',
                  background: 'transparent',
                  border: '1.5px solid var(--cgiar-gray)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--color-text-secondary)',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  onClose();
                  onContinue();
                }}
                disabled={!parsed || !!parseError || loading}
                style={{
                  padding: '8px 24px',
                  background:
                    parsed && !parseError && !loading
                      ? 'linear-gradient(135deg, var(--cgiar-green) 0%, #629600 100%)'
                      : 'var(--cgiar-gray)',
                  color: parsed && !parseError && !loading ? 'white' : 'var(--color-text-muted)',
                  border: 'none',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  cursor: parsed && !parseError && !loading ? 'pointer' : 'not-allowed',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  boxShadow:
                    parsed && !parseError && !loading ? 'var(--shadow-sm)' : 'none',
                  transition: 'all 0.2s',
                }}
              >
                <Play size={15} />
                Continue & Analyze
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
