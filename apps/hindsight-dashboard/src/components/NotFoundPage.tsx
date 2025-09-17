import React from 'react';

const NotFoundPage: React.FC = () => (
  <div className="min-h-screen bg-gray-100 flex items-start justify-center pt-8">
    <div className="bg-white rounded-lg shadow-md p-8 max-w-md text-center">
      <h1 className="text-2xl font-semibold text-gray-800 mb-3">Page Not Found</h1>
      <p className="text-gray-600 mb-6">The page you are looking for doesn&apos;t exist or is not available.</p>
      <a
        href="/dashboard"
        className="inline-flex items-center justify-center px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-md transition-colors"
      >
        Go to Dashboard
      </a>
    </div>
  </div>
);

export default NotFoundPage;
