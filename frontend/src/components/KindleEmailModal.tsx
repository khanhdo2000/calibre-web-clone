import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Mail, AlertCircle, Info } from 'lucide-react';
import { kindleEmailApi } from '@/services/api';

interface KindleEmailModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (email: string) => void;
}

export function KindleEmailModal({ isOpen, onClose, onSuccess }: KindleEmailModalProps) {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadSettings();
    }
  }, [isOpen]);

  const loadSettings = async () => {
    setLoading(true);
    setError(null);
    try {
      const settings = await kindleEmailApi.getKindleEmailSettings();
      setEmail(settings.kindle_email || '');
    } catch (err: any) {
      setError(err.response?.data?.detail || t('kindle.email.loadError'));
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!email.trim()) {
      setError(t('kindle.email.required'));
      return;
    }

    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError(t('kindle.email.invalid'));
      return;
    }

    setSaving(true);
    setError(null);

    try {
      await kindleEmailApi.updateKindleEmailSettings(email.trim());
      onSuccess(email.trim());
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || t('kindle.email.saveError'));
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Mail className="w-5 h-5" />
            {t('kindle.email.settings')}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6">
          {loading ? (
            <div className="text-center py-4">
              <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
              <p className="text-gray-600">{t('common.loading')}</p>
            </div>
          ) : (
            <>
              {/* Approved sender instructions */}
              <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-start gap-2">
                  <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                  <div className="text-sm">
                    <p className="font-medium text-blue-800 mb-1">
                      {t('kindle.email.approvedSenderTitle')}
                    </p>
                    <p
                      className="text-blue-700 mb-2"
                      dangerouslySetInnerHTML={{ __html: t('kindle.email.approvedSenderText') }}
                    />
                    <p
                      className="text-blue-600 text-xs"
                      dangerouslySetInnerHTML={{ __html: t('kindle.email.approvedSenderSteps') }}
                    />
                  </div>
                </div>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {t('kindle.email.label')}
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setError(null);
                  }}
                  placeholder="your-kindle@kindle.com"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      handleSave();
                    }
                  }}
                />
                <p className="text-xs text-gray-500 mt-1">
                  {t('kindle.email.hint')}
                </p>
              </div>

              {error && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
                  <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}

              <div className="flex gap-3">
                <button
                  onClick={onClose}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
                  disabled={saving}
                >
                  {t('common.cancel')}
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving || !email.trim()}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? t('common.saving') : t('common.save')}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}



