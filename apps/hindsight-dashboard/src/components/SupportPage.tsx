import React from 'react';
import { useNavigate } from 'react-router-dom';

const SupportPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="max-w-3xl mx-auto">
      <div className="bg-white rounded-lg shadow-sm p-6 sm:p-8">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center text-amber-700">
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 8h13a4 4 0 010 8H16a5 5 0 01-5 5H8a5 5 0 01-5-5V8z" />
              <path d="M16 8h2a3 3 0 010 6h-2" />
              <path d="M6 1s1 1 0 2 1 1 0 2 1 1 0 2" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-800">Support Hindsight AI</h1>
        </div>

        <p className="text-gray-700 leading-relaxed">
          Hindsight AI is free and actively under development. Donations help me
          focus more time on building features, improving reliability, and covering
          basic infrastructure costs (servers, email, etc.). If you find it useful,
          your support lets me accelerate development and ship improvements faster.
        </p>

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <a
            href="https://buymeacoffee.com/jeanibarz"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium text-white bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-600 hover:to-yellow-600 shadow-md hover:shadow-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-400"
            aria-label="Buy me a coffee"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 8h13a4 4 0 010 8H16a5 5 0 01-5 5H8a5 5 0 01-5-5V8z" />
              <path d="M16 8h2a3 3 0 010 6h-2" />
              <path d="M6 1s1 1 0 2 1 1 0 2 1 1 0 2" />
            </svg>
            <span>Buy me a coffee</span>
          </a>

          <button
            onClick={() => navigate('/dashboard')}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 border border-gray-200 transition"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M15 18l-6-6 6-6" />
            </svg>
            Back to dashboard
          </button>
        </div>

        <p className="mt-4 text-sm text-gray-500">
          No pressure — thanks for using Hindsight AI and for any support!
        </p>
      </div>
    </div>
  );
};

export default SupportPage;

