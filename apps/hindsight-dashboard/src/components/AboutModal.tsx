import React, { useEffect, useRef, useState } from 'react';
import Portal from './Portal';
import { getBuildInfo } from '../api/metaService';
import memoryService from '../api/memoryService';
import notificationService from '../services/notificationService';
import { VITE_VERSION, VITE_BUILD_SHA, VITE_BUILD_TIMESTAMP, VITE_DASHBOARD_IMAGE_TAG } from '../lib/viteEnv';
import { useAuth } from '../context/AuthContext';

interface BuildInfo {
  service_name: string;
  version: string;
  build_sha: string;
  build_timestamp: string;
  image_tag: string;
  error?: string;
}

interface AboutModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const formatTimestamp = (ts: string | undefined | null): string => {
  if (!ts || ts === 'unknown') return 'unknown';
  // Trim sub-second noise from ISO timestamps; leave non-ISO values alone.
  const m = ts.match(/^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})(\.\d+)?(Z|[+-]\d{2}:?\d{2})?$/);
  if (!m) return ts;
  return `${m[1]}${m[3] ?? ''}`;
};

const shortSha = (sha: string | undefined | null): string => {
  if (!sha || sha === 'unknown') return 'unknown';
  return sha.length > 12 ? `${sha.slice(0, 12)}…` : sha;
};

const buildPlainTextDump = (
  backend: BuildInfo | null,
  frontend: BuildInfo | null,
  user: { email?: string } | null | undefined,
  message: string,
): string => {
  const f = frontend || ({} as Partial<BuildInfo>);
  const b = backend || ({} as Partial<BuildInfo>);
  const currentUrl = typeof window !== 'undefined' ? (window.location.href || '') : '';
  const ua = typeof navigator !== 'undefined' ? (navigator.userAgent || '') : '';
  return [
    message?.trim() ? message.trim() : '(no message provided)',
    '',
    '--- Context ---',
    `User: ${user?.email || 'unknown'}`,
    `URL: ${currentUrl}`,
    `User Agent: ${ua}`,
    '',
    '--- Frontend ---',
    `Service: ${f.service_name || 'unknown'}`,
    `Version: ${f.version || 'unknown'}`,
    `Build SHA: ${f.build_sha || 'unknown'}`,
    `Build Timestamp: ${f.build_timestamp || 'unknown'}`,
    `Image Tag: ${f.image_tag || 'unknown'}`,
    '',
    '--- Backend ---',
    `Service: ${b.service_name || 'unknown'}`,
    `Version: ${b.version || 'unknown'}`,
    `Build SHA: ${b.build_sha || 'unknown'}`,
    `Build Timestamp: ${b.build_timestamp || 'unknown'}`,
    `Image Tag: ${b.image_tag || 'unknown'}`,
  ].join('\n');
};

const InfoRow: React.FC<{ label: string; value: string; mono?: boolean; title?: string }> = ({ label, value, mono, title }) => (
  <div className="flex items-baseline justify-between gap-3 py-1.5">
    <dt className="text-xs uppercase tracking-wide text-gray-500 shrink-0">{label}</dt>
    <dd
      className={`text-sm text-gray-800 text-right truncate ${mono ? 'font-mono' : ''}`}
      title={title ?? value}
    >
      {value}
    </dd>
  </div>
);

const SectionSkeleton: React.FC = () => (
  <div className="space-y-2 animate-pulse" aria-hidden="true">
    {[0, 1, 2, 3, 4].map((i) => (
      <div key={i} className="flex justify-between gap-3 py-1.5">
        <div className="h-3 w-20 bg-gray-200 rounded" />
        <div className="h-3 w-32 bg-gray-200 rounded" />
      </div>
    ))}
  </div>
);

const AboutModal: React.FC<AboutModalProps> = ({ isOpen, onClose }) => {
  const [backendInfo, setBackendInfo] = useState<BuildInfo | null>(null);
  const [frontendInfo, setFrontendInfo] = useState<BuildInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [sending, setSending] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [message, setMessage] = useState<string>('');
  const { user } = useAuth() as { user: { email?: string } | null };

  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const previouslyFocusedRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    previouslyFocusedRef.current = (document.activeElement as HTMLElement) || null;
    const t = window.setTimeout(() => closeButtonRef.current?.focus(), 0);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onClose();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => {
      window.clearTimeout(t);
      window.removeEventListener('keydown', onKey);
      try { previouslyFocusedRef.current?.focus(); } catch { /* ignore */ }
    };
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isOpen) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const backendData = await getBuildInfo();
        if (!cancelled) setBackendInfo(backendData);
      } catch (err) {
        console.error('Error fetching backend build info:', err);
        if (!cancelled) {
          setBackendInfo({
            service_name: 'Hindsight Service',
            version: 'unknown',
            build_sha: 'unknown',
            build_timestamp: 'unknown',
            image_tag: 'unknown',
            error: 'Failed to fetch backend build information',
          });
        }
      }
      if (!cancelled) {
        setFrontendInfo({
          service_name: 'AI Agent Memory Dashboard',
          version: VITE_VERSION || 'unknown',
          build_sha: VITE_BUILD_SHA || 'unknown',
          build_timestamp: VITE_BUILD_TIMESTAMP || 'unknown',
          image_tag: VITE_DASHBOARD_IMAGE_TAG || 'unknown',
        });
        setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [isOpen]);

  if (!isOpen) return null;

  const handleContactSupport = async () => {
    if (sending) return;
    try {
      setSending(true);
      const payload: Record<string, any> = {
        message: message?.trim() || '',
        frontend: frontendInfo || {},
        context: {
          current_url: typeof window !== 'undefined' ? (window.location.href || '') : '',
          user_agent: typeof navigator !== 'undefined' ? (navigator.userAgent || '') : '',
          user_email: user?.email || null,
        },
      };
      await memoryService.contactSupport(payload);
      notificationService.showSuccess('Support request sent. Our team will reach out.');
    } catch (e: any) {
      notificationService.showError(e?.message || 'Failed to send support request');
    } finally {
      setSending(false);
    }
  };

  const handleCopyDiagnostics = async () => {
    const text = buildPlainTextDump(backendInfo, frontendInfo, user, message);
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      notificationService.showError('Failed to copy diagnostics to clipboard');
    }
  };

  const buildMailtoHref = () => {
    const to = 'support@hindsight-ai.com';
    const f = frontendInfo || ({} as Partial<BuildInfo>);
    const subject = `Hindsight AI Support – v${f.version || 'unknown'} (sha ${(f.build_sha || '').toString().slice(0, 7) || 'unknown'})`;
    const body = buildPlainTextDump(backendInfo, frontendInfo, user, message);
    return `mailto:${to}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  };

  const renderBuildCard = (title: string, info: BuildInfo | null) => (
    <div className="rounded-lg border border-gray-200 bg-gray-50/60 p-4">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-semibold text-gray-700">{title}</h4>
        {info?.error && (
          <span
            className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-800 border border-yellow-200"
            title={info.error}
          >
            unavailable
          </span>
        )}
      </div>
      {!info ? (
        <SectionSkeleton />
      ) : (
        <dl className="divide-y divide-gray-200/70">
          <InfoRow label="Service" value={info.service_name || 'unknown'} />
          <InfoRow label="Version" value={info.version || 'unknown'} mono />
          <InfoRow label="Build SHA" value={shortSha(info.build_sha)} title={info.build_sha} mono />
          <InfoRow label="Build" value={formatTimestamp(info.build_timestamp)} />
          <InfoRow label="Image Tag" value={info.image_tag || 'unknown'} mono />
        </dl>
      )}
    </div>
  );

  return (
    <Portal>
      <div
        className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50"
        onClick={onClose}
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="about-modal-title"
          className="bg-white rounded-lg shadow-xl w-full mx-4 max-h-[90vh] overflow-y-auto overscroll-contain max-w-2xl md:max-w-3xl"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <div className="min-w-0">
              <h2 id="about-modal-title" className="text-xl font-semibold text-gray-800">
                About Hindsight AI
              </h2>
              <p className="text-xs text-gray-500 mt-1">
                Build information for the dashboard and the backend service currently serving you.
              </p>
            </div>
            <button
              ref={closeButtonRef}
              type="button"
              aria-label="Close"
              className="text-gray-400 hover:text-gray-600 text-2xl leading-none px-2"
              onClick={onClose}
            >
              &times;
            </button>
          </div>

          <div className="p-6 space-y-6">
            {/* Build info card */}
            <section aria-labelledby="about-build-heading">
              <div className="flex items-center justify-between mb-3">
                <h3 id="about-build-heading" className="text-base font-medium text-gray-800">
                  Build information
                </h3>
                <button
                  type="button"
                  onClick={handleCopyDiagnostics}
                  disabled={loading}
                  className="text-xs px-2.5 py-1 rounded border border-gray-300 text-gray-700 hover:bg-gray-100 disabled:opacity-60 transition"
                  title="Copy backend + frontend build info as plain text"
                >
                  {copied ? 'Copied' : 'Copy diagnostics'}
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {renderBuildCard('Backend service', backendInfo)}
                {renderBuildCard('Frontend dashboard', frontendInfo)}
              </div>
            </section>

            {/* Contact support card */}
            <section
              aria-labelledby="about-support-heading"
              className="rounded-lg border border-gray-200 bg-white p-4"
            >
              <h3 id="about-support-heading" className="text-base font-medium text-gray-800 mb-1">
                Contact support
              </h3>
              <p className="text-xs text-gray-500 mb-3">
                Your message is sent with the build information above so we can reproduce the issue quickly.
              </p>
              <textarea
                className="w-full border border-gray-300 rounded-md p-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                placeholder="Briefly describe the problem, steps to reproduce, and expected behavior."
                rows={4}
                maxLength={4000}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
              />
              <div className="mt-1 text-xs text-gray-400 text-right">{message.length}/4000</div>
              <div className="mt-3 flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition disabled:opacity-60"
                  onClick={handleContactSupport}
                  disabled={sending}
                  title="Send details to support@hindsight-ai.com"
                >
                  {sending ? 'Sending…' : 'Send support request'}
                </button>
                <a
                  href={buildMailtoHref()}
                  className="text-sm text-blue-600 hover:text-blue-800"
                  title="Compose email using your mail app"
                >
                  Open in mail app
                </a>
              </div>
            </section>
          </div>

          <div className="flex justify-end items-center p-6 border-t border-gray-200">
            <button
              type="button"
              className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 transition"
              onClick={onClose}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </Portal>
  );
};

export default AboutModal;
