import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, Link } from 'react-router-dom';
import { booksApi, kindleEmailApi } from '@/services/api';
import { BookOpen, Download, Calendar, Tag, User, BookMarked, Mail, CheckCircle, AlertCircle, Settings, Info } from 'lucide-react';
import type { BookDetail } from '@/types';
import { KindleEmailModal } from '@/components/KindleEmailModal';

export function BookDetailPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const [book, setBook] = useState<BookDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [kindleEmail, setKindleEmail] = useState<string | null>(null);
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [sendingToKindle, setSendingToKindle] = useState(false);
  const [sendStatus, setSendStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  useEffect(() => {
    if (id) {
      loadBook(parseInt(id));
      loadKindleEmail();
    }
  }, [id]);

  const loadBook = async (bookId: number) => {
    setLoading(true);
    setError(null);

    try {
      const data = await booksApi.getBook(bookId);
      setBook(data);
    } catch (err) {
      setError(t('book.detail.failedToLoad'));
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadKindleEmail = async () => {
    try {
      const settings = await kindleEmailApi.getKindleEmailSettings();
      setKindleEmail(settings.kindle_email);
    } catch (err) {
      // Silently fail - user can set email when needed
      console.error('Failed to load Kindle email:', err);
    }
  };

  const handleSendToKindle = async () => {
    if (!book) return;

    // Check if EPUB is available
    if (!book.file_formats.includes('EPUB')) {
      setSendStatus({
        type: 'error',
        message: t('kindle.send.epubNotAvailable'),
      });
      setTimeout(() => setSendStatus(null), 5000);
      return;
    }

    // Check if email is set
    if (!kindleEmail) {
      setShowEmailModal(true);
      return;
    }

    setSendingToKindle(true);
    setSendStatus(null);

    try {
      const result = await kindleEmailApi.sendToKindle(book.id);
      setSendStatus({
        type: 'success',
        message: result.message || t('kindle.send.success'),
      });
      setTimeout(() => setSendStatus(null), 5000);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || t('kindle.send.error');
      setSendStatus({
        type: 'error',
        message: errorMessage,
      });
      setTimeout(() => setSendStatus(null), 5000);
    } finally {
      setSendingToKindle(false);
    }
  };

  const handleEmailSaved = (email: string) => {
    setKindleEmail(email);
    // Automatically send after setting email
    setTimeout(() => {
      handleSendToKindle();
    }, 100);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">{t('book.detail.loading')}</p>
        </div>
      </div>
    );
  }

  if (error || !book) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center text-red-600">
          <p className="text-xl font-semibold mb-2">{t('common.error')}</p>
          <p>{error || t('book.detail.notFound')}</p>
        </div>
      </div>
    );
  }

  // Use S3 cover URL if available, otherwise fall back to API endpoint
  const coverUrl = book.cover_url || (book.has_cover ? booksApi.getCoverUrl(book.id) : null);

  return (
    <div className="max-w-6xl mx-auto">
      <div className="bg-white rounded-lg shadow-lg p-8">
        <div className="grid md:grid-cols-3 gap-8">
          {/* Cover */}
          <div className="md:col-span-1">
            <div className="aspect-[2/3] bg-gray-200 rounded-lg overflow-hidden">
              {coverUrl ? (
                <img
                  src={coverUrl}
                  alt={book.title}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <BookOpen className="w-24 h-24 text-gray-400" />
                </div>
              )}
            </div>

            <div className="mt-4 space-y-2">
              {book.file_formats.includes('EPUB') && (
                <Link
                  to={`/read/${book.id}`}
                  className="block w-full bg-blue-600 text-white px-4 py-3 rounded-lg text-center font-medium hover:bg-blue-700 transition-colors"
                >
                  <BookOpen className="w-5 h-5 inline mr-2" />
                  {t('book.detail.readBook')}
                </Link>
              )}

              {book.file_formats.includes('EPUB') && (
                <div>
                  <button
                    onClick={handleSendToKindle}
                    disabled={sendingToKindle}
                    className="block w-full bg-orange-600 text-white px-4 py-3 rounded-lg text-center font-medium hover:bg-orange-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Mail className="w-5 h-5 inline mr-2" />
                    {sendingToKindle ? t('kindle.send.sending') : t('kindle.send.button')}
                  </button>
                  {kindleEmail && (
                    <div className="mt-2 text-xs text-gray-500">
                      <div className="flex items-center gap-1 mb-1">
                        <Info className="w-3 h-3" />
                        <span
                          dangerouslySetInnerHTML={{
                            __html: t('kindle.email.approvedSenderNote', {
                              defaultValue: 'Add <strong>sach@mnd.vn</strong> to your <a href="https://www.amazon.com/hz/mycd/myx#/home/settings/payment" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:underline">Kindle approved email list</a>'
                            })
                          }}
                        />
                      </div>
                      <button
                        onClick={() => setShowEmailModal(true)}
                        className="text-blue-600 hover:underline flex items-center gap-1"
                      >
                        <Settings className="w-3 h-3" />
                        {t('kindle.email.changeEmail', { defaultValue: 'Change Kindle email' })}
                      </button>
                    </div>
                  )}
                </div>
              )}

              {sendStatus && (
                <div
                  className={`p-3 rounded-lg flex items-start gap-2 ${
                    sendStatus.type === 'success'
                      ? 'bg-green-50 border border-green-200'
                      : 'bg-red-50 border border-red-200'
                  }`}
                >
                  {sendStatus.type === 'success' ? (
                    <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                  ) : (
                    <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  )}
                  <p
                    className={`text-sm ${
                      sendStatus.type === 'success' ? 'text-green-700' : 'text-red-700'
                    }`}
                  >
                    {sendStatus.message}
                  </p>
                </div>
              )}

              {book.file_formats.map((format) => (
                <a
                  key={format}
                  href={booksApi.getGDriveDirectUrl(book.id, format.toLowerCase())}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block w-full bg-gray-600 text-white px-4 py-3 rounded-lg text-center font-medium hover:bg-gray-700 transition-colors"
                >
                  <Download className="w-5 h-5 inline mr-2" />
                  {t('book.detail.download', { format })}
                </a>
              ))}
            </div>
          </div>

          {/* Details */}
          <div className="md:col-span-2">
            <h1 className="text-3xl font-bold text-gray-800 mb-4">{book.title}</h1>

            <div className="space-y-3 mb-6">
              {book.authors.length > 0 && (
                <div className="flex items-start gap-2">
                  <User className="w-5 h-5 text-gray-500 mt-0.5" />
                  <div>
                    <span className="text-gray-600 font-medium">{t('book.detail.authors')} </span>
                    <span className="text-gray-800">
                      {book.authors.map((author, index) => (
                        <span key={author.id}>
                          <Link
                            to={`/author/stored/${author.id}`}
                            className="hover:text-blue-600 hover:underline"
                          >
                            {author.name}
                          </Link>
                          {index < book.authors.length - 1 && ', '}
                        </span>
                      ))}
                    </span>
                  </div>
                </div>
              )}

              {book.series && (
                <div className="flex items-start gap-2">
                  <BookMarked className="w-5 h-5 text-gray-500 mt-0.5" />
                  <div>
                    <span className="text-gray-600 font-medium">{t('book.detail.series')} </span>
                    <span className="text-gray-800">
                      {book.series.name}
                      {book.series.index && ` #${book.series.index}`}
                    </span>
                  </div>
                </div>
              )}

              {book.publisher && (
                <div className="flex items-start gap-2">
                  <BookOpen className="w-5 h-5 text-gray-500 mt-0.5" />
                  <div>
                    <span className="text-gray-600 font-medium">{t('book.detail.publisher')} </span>
                    <Link
                      to={`/publisher/new/${book.publisher.id}`}
                      className="text-gray-800 hover:text-blue-600 hover:underline"
                    >
                      {book.publisher.name}
                    </Link>
                  </div>
                </div>
              )}

              {book.pubdate && (
                <div className="flex items-start gap-2">
                  <Calendar className="w-5 h-5 text-gray-500 mt-0.5" />
                  <div>
                    <span className="text-gray-600 font-medium">{t('book.detail.published')} </span>
                    <span className="text-gray-800">
                      {new Date(book.pubdate).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              )}

              {book.rating && (
                <div className="flex items-start gap-2">
                  <span className="text-gray-600 font-medium">{t('book.detail.rating')} </span>
                  <span className="text-yellow-500">
                    {'★'.repeat(Math.round(book.rating))}
                    {'☆'.repeat(5 - Math.round(book.rating))}
                  </span>
                </div>
              )}
            </div>

            {book.tags.length > 0 && (
              <div className="mb-6">
                <div className="flex items-start gap-2 mb-2">
                  <Tag className="w-5 h-5 text-gray-500 mt-0.5" />
                  <span className="text-gray-600 font-medium">{t('book.detail.tags')}:</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {book.tags.map((tag) => (
                    <Link
                      key={tag.id}
                      to={`/category/new/${tag.id}`}
                      className="bg-gray-100 text-gray-700 px-3 py-1 rounded-full text-sm hover:bg-blue-100 hover:text-blue-700 transition-colors"
                    >
                      {tag.name}
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {book.comments && (
              <div className="mb-6">
                <h2 className="text-xl font-semibold mb-2">{t('book.detail.description')}</h2>
                <div
                  className="text-gray-700 prose max-w-none"
                  dangerouslySetInnerHTML={{ __html: book.comments }}
                />
              </div>
            )}

            {Object.keys(book.identifiers).length > 0 && (
              <div>
                <h2 className="text-xl font-semibold mb-2">{t('book.detail.identifiers')}</h2>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {Object.entries(book.identifiers).map(([key, value]) => (
                    <div key={key}>
                      <span className="text-gray-600 font-medium">{key.toUpperCase()}: </span>
                      <span className="text-gray-800">{value}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <KindleEmailModal
        isOpen={showEmailModal}
        onClose={() => setShowEmailModal(false)}
        onSuccess={handleEmailSaved}
      />
    </div>
  );
}
