'use client';

interface LoadingOverlayProps {
  text: string;
}

export function LoadingOverlay({ text }: LoadingOverlayProps) {
  return (
    <div className="bulk-loading-overlay">
      <div className="bulk-spinner" />
      <p>{text}</p>
    </div>
  );
}
