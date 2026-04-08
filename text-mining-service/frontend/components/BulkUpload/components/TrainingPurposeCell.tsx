'use client';

import { useState, useCallback } from 'react';

const FIXED_OPTIONS = [
  'Training enumerators',
  'Engaging with change agents',
  'Training of trainers',
];

interface TrainingPurposeCellProps {
  value: string | undefined;
  globalIdx: number;
  onEdit: (globalIdx: number, field: string, value: string) => void;
}

function parseValue(raw: string | undefined): { option: string; otherText: string } {
  if (!raw) return { option: '', otherText: '' };
  if (raw.startsWith('Other: ')) return { option: 'Other', otherText: raw.slice(7) };
  if (raw === 'Other') return { option: 'Other', otherText: '' };
  if (FIXED_OPTIONS.includes(raw)) return { option: raw, otherText: '' };
  // Unknown value — treat as Other
  return { option: 'Other', otherText: raw };
}

export function TrainingPurposeCell({ value, globalIdx, onEdit }: TrainingPurposeCellProps) {
  const parsed = parseValue(value);
  const [option, setOption] = useState(parsed.option);
  const [otherText, setOtherText] = useState(parsed.otherText);

  const handleOptionChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const selected = e.target.value;
      setOption(selected);
      if (selected !== 'Other') {
        setOtherText('');
        onEdit(globalIdx, 'training_purpose', selected);
      } else {
        // Keep current otherText; only emit if there's already text
        if (otherText) onEdit(globalIdx, 'training_purpose', `Other: ${otherText}`);
      }
    },
    [globalIdx, onEdit, otherText],
  );

  const handleOtherChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const text = e.target.value;
      setOtherText(text);
      onEdit(globalIdx, 'training_purpose', text ? `Other: ${text}` : 'Other');
    },
    [globalIdx, onEdit],
  );

  return (
    <div className="bulk-training-purpose-cell">
      <select value={option} onChange={handleOptionChange}>
        <option value="">Select...</option>
        {FIXED_OPTIONS.map((opt) => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
        <option value="Other">Other</option>
      </select>
      {option === 'Other' && (
        <input
          type="text"
          className="bulk-training-purpose-other"
          placeholder="Describe purpose..."
          value={otherText}
          onChange={handleOtherChange}
        />
      )}
    </div>
  );
}
