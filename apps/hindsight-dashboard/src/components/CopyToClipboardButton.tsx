import React, { useState } from 'react';

interface CopyToClipboardButtonProps {
  textToCopy: string;
  displayId: string;
}

export const CopyToClipboardButton: React.FC<CopyToClipboardButtonProps> = ({ textToCopy, displayId }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000); // Reset "Copied!" message after 2 seconds
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  return (
    <span className="copy-id-container">
      <span className="truncated-id" title={textToCopy}>{displayId}</span>
      <button onClick={handleCopy} className="copy-button">
        {copied ? 'Copied!' : '📋'}
      </button>
    </span>
  );
};
