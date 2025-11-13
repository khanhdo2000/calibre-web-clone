import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080/api';

export function PairPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [deviceKey, setDeviceKey] = useState(searchParams.get('key') || '');
  const [error, setError] = useState('');
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    // If key is in URL, auto-connect
    const keyFromUrl = searchParams.get('key');
    if (keyFromUrl) {
      setDeviceKey(keyFromUrl);
      handleConnect(keyFromUrl);
    }
  }, [searchParams]);

  const handleConnect = async (key?: string) => {
    const keyToUse = key || deviceKey.trim().toUpperCase();

    if (!keyToUse) {
      setError('Vui lòng nhập mã thiết bị');
      return;
    }

    setConnecting(true);
    setError('');

    try {
      const response = await axios.post(`${API_URL}/kindle-pair/connect`, {
        device_key: keyToUse,
      });

      if (response.data.success) {
        // Navigate to book selection page
        navigate(`/select-books?key=${keyToUse}`);
      }
    } catch (err) {
      console.error('Error connecting:', err);
      if (axios.isAxiosError(err) && err.response?.status === 404) {
        setError('Mã thiết bị không hợp lệ hoặc đã hết hạn');
      } else {
        setError('Kết nối thất bại. Vui lòng thử lại.');
      }
      setConnecting(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleConnect();
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
        <h1 className="text-3xl font-bold mb-2 text-center">Ghép nối Kindle</h1>
        <p className="text-gray-600 text-center mb-6">
          Nhập mã hiển thị trên thiết bị Kindle của bạn
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="deviceKey" className="block text-sm font-medium text-gray-700 mb-2">
              Mã thiết bị
            </label>
            <input
              id="deviceKey"
              type="text"
              value={deviceKey}
              onChange={(e) => setDeviceKey(e.target.value.toUpperCase())}
              placeholder="Nhập mã 6 ký tự"
              maxLength={6}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg text-center text-2xl font-mono tracking-widest uppercase focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              disabled={connecting}
              autoFocus
            />
          </div>

          {error && (
            <div className="text-red-600 text-sm text-center bg-red-50 p-3 rounded">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={connecting || !deviceKey.trim()}
            className="w-full py-3 px-4 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {connecting ? 'Đang kết nối...' : 'Kết nối'}
          </button>
        </form>

        <div className="mt-6 pt-6 border-t border-gray-200">
          <p className="text-xs text-gray-500 text-center">
            Đảm bảo Kindle của bạn đang ở màn hình ghép nối và mã khớp chính xác.
          </p>
        </div>
      </div>
    </div>
  );
}
