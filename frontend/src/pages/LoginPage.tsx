import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/contexts/AuthContext';
import { authApi } from '@/services/api';
import { BookOpen, Mail, Lock, AlertCircle, RefreshCw } from 'lucide-react';

export function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [needsVerification, setNeedsVerification] = useState(false);
  const [resendingVerification, setResendingVerification] = useState(false);
  const [verificationResent, setVerificationResent] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setNeedsVerification(false);
    setVerificationResent(false);
    setLoading(true);

    try {
      await login(email, password);
      navigate('/');
    } catch (err: any) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail || t('auth.login.error');

      if (status === 403 && detail.includes('not verified')) {
        setNeedsVerification(true);
        setError(detail);
      } else {
        setError(detail);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleResendVerification = async () => {
    setResendingVerification(true);
    try {
      await authApi.resendVerification(email);
      setVerificationResent(true);
    } catch (err: any) {
      // Don't show error - the API doesn't reveal if email exists
      setVerificationResent(true);
    } finally {
      setResendingVerification(false);
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
            {t('auth.login.title')}
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            {t('auth.login.subtitle')}
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-700">{error}</p>
              </div>
              {needsVerification && !verificationResent && (
                <button
                  type="button"
                  onClick={handleResendVerification}
                  disabled={resendingVerification || !email}
                  className="mt-3 w-full flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {resendingVerification ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      {t('auth.verification.resending')}
                    </>
                  ) : (
                    <>
                      <Mail className="w-4 h-4" />
                      {t('auth.verification.resendEmail')}
                    </>
                  )}
                </button>
              )}
              {verificationResent && (
                <div className="mt-3 p-2 bg-green-50 border border-green-200 rounded-lg">
                  <p className="text-sm text-green-700">{t('auth.verification.resendSuccess')}</p>
                </div>
              )}
              {needsVerification && (
                <div className="mt-3 text-center">
                  <Link
                    to={`/resend-verification${email ? `?email=${encodeURIComponent(email)}` : ''}`}
                    className="text-sm text-blue-600 hover:text-blue-700"
                  >
                    {t('auth.verification.goToResendPage')}
                  </Link>
                </div>
              )}
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                {t('auth.login.email')}
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
                  placeholder={t('auth.login.emailPlaceholder')}
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                {t('auth.login.password')}
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
                  placeholder={t('auth.login.passwordPlaceholder')}
                />
              </div>
            </div>
          </div>

          <div className="flex items-center justify-end">
            <Link
              to="/forgot-password"
              className="text-sm text-blue-600 hover:text-blue-500"
            >
                    {t('auth.password.forgot.title')}
            </Link>
          </div>

          <div>
            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  {t('auth.login.loggingIn')}
                </div>
              ) : (
                t('auth.login.button')
              )}
            </button>
          </div>

          <div className="text-center text-sm">
            <span className="text-gray-600">{t('auth.login.noAccount')} </span>
            <Link to="/register" className="font-medium text-blue-600 hover:text-blue-500">
              {t('auth.login.registerLink')}
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}

