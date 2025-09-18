import { useEffect, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

interface PortalProps {
  children: ReactNode;
  /** Optional container to mount into. Defaults to document.body */
  container?: Element | null;
}

// Lightweight portal that safely avoids SSR issues
const Portal = ({ children, container }: PortalProps) => {
  const [mounted, setMounted] = useState(false);
  const defaultContainerRef = useRef<Element | null>(null);

  useEffect(() => {
    setMounted(true);
    if (!container) {
      defaultContainerRef.current = typeof document !== 'undefined' ? document.body : null;
    }
    return () => setMounted(false);
  }, [container]);

  if (!mounted) return null;

  const mountNode = container ?? defaultContainerRef.current;
  if (!mountNode) return null;

  return createPortal(children, mountNode);
};

export default Portal;
