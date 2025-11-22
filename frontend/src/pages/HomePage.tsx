import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { categoryGroupsApi } from '@/services/api';
import type { CategoryGroup, Book } from '@/types';
import { BookCard } from '@/components/BookCard';
import { FolderTree, ChevronRight } from 'lucide-react';

interface CategoryWithBooks {
  category: CategoryGroup;
  books: Book[];
}

export function HomePage() {
  const { t } = useTranslation();
  const [categoriesWithBooks, setCategoriesWithBooks] = useState<CategoryWithBooks[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const booksPerCategory = 12; // Show 12 books per category on homepage

  useEffect(() => {
    loadCategoriesWithBooks();
  }, []);

  const loadCategoriesWithBooks = async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch all categories
      const categoriesData = await categoryGroupsApi.getAll();
      const categories = categoriesData.categories;

      if (categories.length === 0) {
        setCategoriesWithBooks([]);
        setLoading(false);
        return;
      }

      // Fetch books for each category using the optimized endpoint (1 API call per category)
      const categoriesWithBooksData: CategoryWithBooks[] = [];

      // Fetch books for all categories in parallel
      const categoryBookPromises = categories
        .filter(category => category.tags.length > 0)
        .map(async (category) => {
          try {
            const result = await categoryGroupsApi.getBooks(category.id, {
              page: 1,
              per_page: booksPerCategory,
              sort: 'new',
            });

            if (result.books.length > 0) {
              return { category, books: result.books };
            }
            return null;
          } catch (err) {
            console.error(`Error loading books for category ${category.id}:`, err);
            return null;
          }
        });

      const results = await Promise.all(categoryBookPromises);
      results.forEach(result => {
        if (result) {
          categoriesWithBooksData.push(result);
        }
      });

      setCategoriesWithBooks(categoriesWithBooksData);
    } catch (err: any) {
      setError(err.response?.data?.detail || t('categories.failedToLoad'));
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto md:px-4 py-4 md:py-8">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
            <p className="text-gray-600">{t('common.loading')}</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto md:px-4 py-4 md:py-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mx-4 md:mx-0">
          {error}
        </div>
      </div>
    );
  }

  if (categoriesWithBooks.length === 0) {
    return (
      <div className="container mx-auto md:px-4 py-4 md:py-8">
        <div className="bg-gray-50 rounded-lg p-8 md:p-12 text-center mx-4 md:mx-0">
          <FolderTree className="w-12 h-12 md:w-16 md:h-16 text-gray-300 mx-auto mb-4" />
          <h2 className="text-lg md:text-xl font-semibold text-gray-700 mb-2">
            {t('categories.empty')}
          </h2>
          <p className="text-sm md:text-base text-gray-500 mb-4">
            {t('categories.createFirst')}
          </p>
          <Link
            to="/books"
            className="inline-block bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors text-sm md:text-base"
          >
            {t('navigation.books')}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto md:px-4 py-4 md:py-8">
      {/* Page Header */}
      <div className="mb-6 md:mb-8 px-4 md:px-0">
        <h1 className="text-2xl md:text-3xl font-bold text-gray-800 mb-2">
          {t('home.title')}
        </h1>
        <p className="text-gray-600 text-sm md:text-base">
          {t('home.subtitle')}
        </p>
      </div>

      {/* Categories with Books */}
      <div className="space-y-8 md:space-y-12">
        {categoriesWithBooks.map(({ category, books }) => (
          <div key={category.id} className="md:bg-white md:rounded-lg md:shadow-sm md:border md:border-gray-200 md:p-6">
            {/* Category Header */}
            <div className="flex items-center justify-between mb-4 px-4 md:px-0 md:mb-6">
              <div className="flex items-center gap-2 md:gap-3">
                <FolderTree className="hidden md:block w-6 h-6 text-blue-600" />
                <div>
                  <h2 className="text-xl md:text-2xl font-bold text-gray-800">
                    {category.name}
                  </h2>
                  {category.description && (
                    <p className="text-gray-600 text-xs md:text-sm mt-1">
                      {category.description}
                    </p>
                  )}
                </div>
              </div>
              <Link
                to={`/categories/${category.id}`}
                className="flex items-center gap-1 md:gap-2 text-blue-600 hover:text-blue-700 font-medium transition-colors text-sm md:text-base"
              >
                <span className="hidden sm:inline">{t('home.viewAll')}</span>
                <ChevronRight className="w-4 h-4 md:w-5 md:h-5" />
              </Link>
            </div>

            {/* Books Horizontal Scroll */}
            <div className="relative md:-mx-2">
              <div className="overflow-x-auto scrollbar-hide pb-2">
                <div className="flex gap-3 pl-4 md:gap-4 md:px-2" style={{ width: 'max-content' }}>
                  {books.map((book) => (
                    <div key={book.id} className="w-32 md:w-40 flex-shrink-0">
                      <BookCard book={book} />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Link to All Books */}
      <div className="mt-8 md:mt-12 text-center px-4 md:px-0">
        <Link
          to="/books"
          className="inline-block bg-gray-100 text-gray-700 px-6 md:px-8 py-2 md:py-3 rounded-lg hover:bg-gray-200 transition-colors font-medium text-sm md:text-base"
        >
          {t('home.browseAllBooks')}
        </Link>
      </div>
    </div>
  );
}
