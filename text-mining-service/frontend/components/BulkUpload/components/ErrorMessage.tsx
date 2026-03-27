'use client';

interface ErrorMessageProps {
  message: string;
}

export function ErrorMessage({ message }: ErrorMessageProps) {
  return (
    <div className="bulk-error-message">
      ❌ {message}
    </div>
  );
}
