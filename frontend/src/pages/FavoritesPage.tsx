import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { favoritesApi } from '@/services/api';
import { BookCard } from '@/components/BookCard';
import { useAuth } from '@/contexts/AuthContext';
import { Heart } from 'lucide-react';
import type { Book } from '@/types';

export function FavoritesPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadFavoriteBooks = async () => {
      if (!user) {
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        // Single API call to get all favorites with book data
        const favoriteBooks = await favoritesApi.getFavoritesWithBooks();
        setBooks(favoriteBooks);
      } catch (err) {
        console.error('Error loading favorite books:', err);
        setError('Failed to load favorite books');
      } finally {
        setLoading(false);
      }
    };

    loadFavoriteBooks();
  }, [user]);

  if (!user) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="text-center py-12">
          <Heart className="w-16 h-16 mx-auto text-gray-300 mb-4" />
          <h2 className="text-2xl font-semibold text-gray-700 mb-2">
            {t('favorites.loginRequired')}
          </h2>
          <p className="text-gray-500">
            {t('favorites.loginMessage')}
          </p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">{t('favorites.title')}</h1>
        <div className="flex justify-center items-center py-12">
          <div className="text-gray-500">{t('favorites.loading')}</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">{t('favorites.title')}</h1>
        <div className="text-center py-12">
          <p className="text-red-500">{t('favorites.loadError')}</p>
        </div>
      </div>
    );
  }

  if (books.length === 0) {
    return (
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">{t('favorites.title')}</h1>
        <div className="text-center py-12">
          <Heart className="w-16 h-16 mx-auto text-gray-300 mb-4" />
          <h2 className="text-2xl font-semibold text-gray-700 mb-2">
            {t('favorites.empty')}
          </h2>
          <p className="text-gray-500">
            {t('favorites.emptyMessage')}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">{t('favorites.title')}</h1>
        <div className="flex items-center gap-2 text-gray-600">
          <Heart className="w-5 h-5 fill-red-500 text-red-500" />
          <span>{t('favorites.bookCount', { count: books.length })}</span>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3 md:gap-4">
        {books.map((book) => (
          <BookCard key={book.id} book={book} />
        ))}
      </div>
    </div>
  );
}
