import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, Link } from 'react-router-dom';
import { booksApi } from '@/services/api';
import { BookOpen, Download, Calendar, Tag, User, BookMarked } from 'lucide-react';
import type { BookDetail } from '@/types';

export function BookDetailPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const [book, setBook] = useState<BookDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      loadBook(parseInt(id));
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

              {book.file_formats.map((format) => (
                <div key={format} className="flex gap-2">
                <a
                  href={booksApi.getDownloadUrl(book.id, format.toLowerCase())}
                  download
                    className="flex-1 bg-gray-600 text-white px-4 py-3 rounded-lg text-center font-medium hover:bg-gray-700 transition-colors"
                >
                  <Download className="w-5 h-5 inline mr-2" />
                  {t('book.detail.download', { format })}
                </a>
                  <a
                    href={booksApi.getGDriveDirectUrl(book.id, format.toLowerCase())}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-3 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50"
                    title="Download via Google Drive"
                  >
                    GDrive
                  </a>
                </div>
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
                    <span className="text-gray-800">{book.publisher.name}</span>
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
                    <span
                      key={tag.id}
                      className="bg-gray-100 text-gray-700 px-3 py-1 rounded-full text-sm"
                    >
                      {tag.name}
                    </span>
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
    </div>
  );
}
