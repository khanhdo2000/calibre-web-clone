import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { booksApi } from '@/services/api';
import { BookCard } from '@/components/BookCard';
import type { BookListResponse } from '@/types';
import { RefreshCw } from 'lucide-react';

export function DiscoverPage() {
  const { t } = useTranslation();
  const [data, setData] = useState<BookListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const perPage = 60;

  useEffect(() => {
    loadRandomBooks();
  }, []);

  const loadRandomBooks = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await booksApi.getRandomBooks(perPage);
      setData(response);
    } catch (err) {
      setError(t('discover.failedToLoad'));
      console.error(err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadRandomBooks();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">{t('discover.loading')}</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center text-red-600">
          <p className="text-xl font-semibold mb-2">{t('common.error')}</p>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!data || data.books.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center text-gray-600">
          <p className="text-xl font-semibold mb-2">{t('discover.noBooksFound')}</p>
          <p>{t('discover.libraryEmpty')}</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">{t('discover.title')}</h1>
          <p className="text-gray-600 mt-1">
            {t('discover.showing', { count: data.books.length })}
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          <span>{t('discover.refresh')}</span>
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-8 gap-y-10">
        {data.books.map((book) => (
          <BookCard key={book.id} book={book} />
        ))}
      </div>
    </div>
  );
}

