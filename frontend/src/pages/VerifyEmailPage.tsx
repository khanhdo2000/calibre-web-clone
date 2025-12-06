import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { authApi } from '@/services/api';

export function VerifyEmailPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');
  const [email, setEmail] = useState('');

  useEffect(() => {
    const token = searchParams.get('token');
    if (token) {
      verifyEmail(token);
    } else {
      setStatus('error');
      setMessage(t('auth.verification.noToken'));
    }
  }, [searchParams, t]);

  const verifyEmail = async (token: string) => {
    try {
      const response = await authApi.verifyEmail(token);
      setStatus('success');
      setMessage(response.message);
      setEmail(response.email);
    } catch (err: any) {
      setStatus('error');
      setMessage(err.response?.data?.detail || t('auth.verification.failed'));
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          {status === 'loading' && (
            <>
              <div className="flex justify-center">
                <Loader2 className="w-16 h-16 text-blue-600 animate-spin" />
              </div>
              <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
                {t('auth.verification.verifying')}
              </h2>
              <p className="mt-2 text-sm text-gray-600">
                {t('auth.verification.pleaseWait')}
              </p>
            </>
          )}

          {status === 'success' && (
            <>
              <div className="flex justify-center">
                <CheckCircle className="w-16 h-16 text-green-600" />
              </div>
              <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
                {t('auth.verification.success')}
              </h2>
              <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                <p className="text-sm text-green-700">
                  {t('auth.verification.successMessage', { email })}
                </p>
              </div>
              <div className="mt-6">
                <Link
                  to="/login"
                  className="inline-flex items-center px-4 py-2 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  {t('auth.verification.proceedToLogin')}
                </Link>
              </div>
            </>
          )}

          {status === 'error' && (
            <>
              <div className="flex justify-center">
                <XCircle className="w-16 h-16 text-red-600" />
              </div>
              <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
                {t('auth.verification.errorTitle')}
              </h2>
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-700">{message}</p>
              </div>
              <p className="mt-4 text-sm text-gray-600">
                {t('auth.verification.tryAgain')}
              </p>
              <div className="mt-6 space-y-3">
                <div className="flex flex-col gap-2">
                  <Link
                    to="/resend-verification"
                    className="inline-flex items-center justify-center px-4 py-2 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  >
                    {t('auth.verification.resendEmail')}
                  </Link>
                  <Link
                    to="/login"
                    className="inline-flex items-center justify-center px-4 py-2 border border-gray-300 rounded-lg shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  >
                    {t('auth.verification.backToLogin')}
                  </Link>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
