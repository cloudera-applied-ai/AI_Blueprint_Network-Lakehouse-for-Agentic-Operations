import { useState } from 'react';
import { systemSettingsService } from '@/services/systemSettingsService';

interface BackendSetupProps {
  onConfigured: () => void;
}

const BackendSetup = ({ onConfigured }: BackendSetupProps) => {
  const [url, setUrl] = useState('');
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConnect = async () => {
    const trimmedUrl = url.trim().replace(/\/+$/, ''); // remove trailing slashes
    if (!trimmedUrl) {
      setError('Please enter a backend URL.');
      return;
    }

    setTesting(true);
    setError(null);

    try {
      // Test the connection by hitting the health endpoint
      const response = await fetch(`${trimmedUrl}/health`, {
        signal: AbortSignal.timeout(10000),
      });

      if (response.ok) {
        // Save and proceed
        systemSettingsService.saveBackendUrlLocally(trimmedUrl);
        onConfigured();
      } else {
        setError(`Backend returned HTTP ${response.status}. Verify the URL is correct.`);
      }
    } catch (err) {
      // Save anyway - the backend might not have /health but could still work
      // Let the user choose to save and try
      setError(
        `Could not reach the backend at that URL. You can save it anyway and retry.`
      );
    } finally {
      setTesting(false);
    }
  };

  const handleSaveAnyway = () => {
    const trimmedUrl = url.trim().replace(/\/+$/, '');
    if (trimmedUrl) {
      systemSettingsService.saveBackendUrlLocally(trimmedUrl);
      onConfigured();
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="bg-gray-800 rounded-xl shadow-2xl border border-gray-700 max-w-lg w-full p-8">
        <h1 className="text-2xl font-bold text-white mb-2">
          Network Data Lakehouse
        </h1>
        <p className="text-gray-400 mb-6">
          Enter the URL of your backend API server to get started. This is the
          URL of the <span className="text-gray-300 font-medium">noc-backend</span> application
          deployed in Cloudera Machine Learning.
        </p>

        <label className="block text-sm font-medium text-gray-300 mb-2">
          Backend API URL
        </label>
        <input
          type="url"
          value={url}
          onChange={(e) => {
            setUrl(e.target.value);
            setError(null);
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !testing) handleConnect();
          }}
          placeholder="https://noc-backend-xxxxx.ml-yyyy.cloudera.site"
          className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          autoFocus
          disabled={testing}
        />

        {error && (
          <div className="mt-3 text-sm">
            <p className="text-yellow-400">{error}</p>
            {error.includes('save it anyway') && (
              <button
                onClick={handleSaveAnyway}
                className="mt-2 text-blue-400 hover:text-blue-300 underline"
              >
                Save and continue anyway
              </button>
            )}
          </div>
        )}

        <button
          onClick={handleConnect}
          disabled={testing || !url.trim()}
          className={`mt-4 w-full py-3 rounded-lg font-medium transition-colors ${
            testing || !url.trim()
              ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-500'
          }`}
        >
          {testing ? 'Testing connection...' : 'Connect'}
        </button>

        <p className="text-gray-500 text-xs mt-4">
          You can find the backend URL in your CML workspace under Applications.
          This setting is saved in your browser.
        </p>
      </div>
    </div>
  );
};

export default BackendSetup;
