import React from 'react';

interface LastUpdatedLabelProps {
  lastUpdated?: Date | null;
  className?: string;
  style?: React.CSSProperties;
}

const LastUpdatedLabel: React.FC<LastUpdatedLabelProps> = ({ lastUpdated, className = '', style }) => {
  if (!lastUpdated) {
    return null;
  }

  const baseClassName = 'text-sm text-gray-500 whitespace-nowrap';
  const mergedClassName = className ? `${baseClassName} ${className}` : baseClassName;

  return (
    <span className={mergedClassName} style={style}>
      {lastUpdated.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
    </span>
  );
};

export default LastUpdatedLabel;
