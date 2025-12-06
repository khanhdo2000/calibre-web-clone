import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { BookOpen, Mail, AlertCircle, CheckCircle, RefreshCw } from 'lucide-react';
import axios from 'axios';

export function ResendVerificationPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();

  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Pre-fill email from URL parameter if provided
  useEffect(() => {
    const emailParam = searchParams.get('email');
    if (emailParam) {
      setEmail(emailParam);
    }
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    setLoading(true);

    try {
      await axios.post('/api/auth/resend-verification', { email });
      setSuccess(true);
      setEmail('');
    } catch (err: any) {
      // API doesn't reveal if email exists for security
      // So we show success message anyway
      setSuccess(true);
      setEmail('');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <div className="flex justify-center">
            <BookOpen className="w-16 h-16 text-blue-600" />
          </div>
          <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
            {t('auth.resendVerification.title')}
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            {t('auth.resendVerification.subtitle')}
          </p>
        </div>

        {success ? (
          <div className="bg-green-50 border border-green-200 rounded-lg p-6">
            <div className="flex items-start gap-3">
              <CheckCircle className="w-6 h-6 text-green-600 flex-shrink-0" />
              <div>
                <h3 className="text-sm font-medium text-green-800">
                  {t('auth.resendVerification.success')}
                </h3>
                <p className="mt-2 text-sm text-green-700">
                  {t('auth.resendVerification.successMessage')}
                </p>
                <p className="mt-2 text-sm text-green-700">
                  {t('auth.resendVerification.linkExpires')}
                </p>
              </div>
            </div>
            <div className="mt-4">
              <Link
                to="/login"
                className="text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                {t('auth.resendVerification.backToLogin')}
              </Link>
            </div>
          </div>
        ) : (
          <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-start gap-2">
                  <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                {t('auth.resendVerification.emailLabel')}
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
                  placeholder={t('auth.resendVerification.emailPlaceholder')}
                />
              </div>
              <p className="mt-2 text-xs text-gray-500">
                {t('auth.resendVerification.emailHint')}
              </p>
            </div>

            <div>
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center items-center gap-2 py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    {t('auth.resendVerification.sending')}
                  </>
                ) : (
                  <>
                    <Mail className="w-4 h-4" />
                    {t('auth.resendVerification.button')}
                  </>
                )}
              </button>
            </div>

            <div className="text-center text-sm space-y-2">
              <div>
                <span className="text-gray-600">
                  {t('auth.resendVerification.alreadyVerified')}
                </span>{' '}
                <Link to="/login" className="font-medium text-blue-600 hover:text-blue-500">
                  {t('auth.resendVerification.login')}
                </Link>
              </div>
              <div>
                <span className="text-gray-600">
                  {t('auth.resendVerification.noAccount')}
                </span>{' '}
                <Link to="/register" className="font-medium text-blue-600 hover:text-blue-500">
                  {t('auth.resendVerification.register')}
                </Link>
              </div>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
