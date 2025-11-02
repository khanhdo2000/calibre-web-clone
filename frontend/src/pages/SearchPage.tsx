import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams, useParams, useNavigate } from 'react-router-dom';
import { booksApi } from '@/services/api';
import { BookCard } from '@/components/BookCard';
import { Pagination } from '@/components/Pagination';
import type { BookListResponse } from '@/types';

export function SearchPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const params = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState<BookListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const query = searchParams.get('query') || '';
  const page = parseInt(params.page || '1');
  const perPage = 60;
  const sortParam = params.sort_param || 'stored';

  useEffect(() => {
    if (query) {
      searchBooks();
    } else {
      // No query - show empty state
      setLoading(false);
      setData(null);
    }
  }, [query, page]);

  const searchBooks = async () => {
    setLoading(true);
    setError(null);

    try {
      // Search with pagination
      const response = await booksApi.getBooks({
        page,
        per_page: perPage,
        sort_by: 'timestamp',
        order: 'desc',
        search_query: query,
      });
      setData(response);
    } catch (err) {
      setError(t('search.noResults'));
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handlePageChange = (newPage: number) => {
    navigate(`/search/${sortParam}${newPage > 1 ? `/page/${newPage}` : ''}?query=${encodeURIComponent(query)}`);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">{t('search.searching')}</p>
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

  if (!query) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center text-gray-600">
          <p className="text-xl font-semibold mb-2">{t('search.search')}</p>
          <p>{t('search.noQuery')}</p>
        </div>
      </div>
    );
  }

  if (!data || data.books.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center text-gray-600">
          <p className="text-xl font-semibold mb-2">{t('search.noResults')}</p>
          <p>{t('search.tryDifferent')}</p>
        </div>
      </div>
    );
  }

  const totalPages = Math.ceil(data.total / perPage);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">
          {t('search.resultsFor', { query })}
        </h1>
        <p className="text-gray-600 mt-1">
          {t('home.showing', {
            start: (page - 1) * perPage + 1,
            end: Math.min(page * perPage, data.total),
            total: data.total
          })}
        </p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-8 gap-y-10">
        {data.books.map((book) => (
          <BookCard key={book.id} book={book} />
        ))}
      </div>

      {totalPages > 1 && (
        <Pagination
          currentPage={page}
          totalPages={totalPages}
          onPageChange={handlePageChange}
        />
      )}
    </div>
  );
}
