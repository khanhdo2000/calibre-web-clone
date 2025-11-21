import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { categoryGroupsApi, booksApi } from '@/services/api';
import type { CategoryGroup, Book } from '@/types';
import { BookCard } from '@/components/BookCard';
import { FolderTree, ArrowLeft, Tag as TagIcon } from 'lucide-react';

export function CategoryViewPage() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const [category, setCategory] = useState<CategoryGroup | null>(null);
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingBooks, setLoadingBooks] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalBooks, setTotalBooks] = useState(0);
  const perPage = 60; // Show more books per page

  useEffect(() => {
    if (id) {
      loadCategory();
    }
  }, [id]);

  useEffect(() => {
    if (category) {
      loadBooks();
    }
  }, [category, page]);

  const loadCategory = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await categoryGroupsApi.getById(parseInt(id!));
      setCategory(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || t('categories.failedToLoad'));
    } finally {
      setLoading(false);
    }
  };

  const loadBooks = async () => {
    if (!category || category.tags.length === 0) {
      setBooks([]);
      setTotalBooks(0);
      setLoadingBooks(false);
      return;
    }

    setLoadingBooks(true);
    try {
      // Fetch books for each tag and combine/deduplicate results
      const tagIds = category.tags.map(t => t.id);
      const allBooksMap = new Map<number, Book>(); // Use Map to deduplicate by book ID

      // Fetch books for each tag
      for (const tagId of tagIds) {
        try {
          const result = await booksApi.getBooks({
            tag_id: tagId,
            page: 1,
            per_page: 100, // Fetch more books per tag
          });

          // Add books to map (deduplicates automatically)
          result.books.forEach(book => {
            allBooksMap.set(book.id, book);
          });
        } catch (err) {
          console.error(`Error fetching books for tag ${tagId}:`, err);
        }
      }

      // Convert map to array and sort by timestamp (newest first)
      const allBooks = Array.from(allBooksMap.values()).sort((a, b) => {
        const timeA = new Date(a.timestamp || 0).getTime();
        const timeB = new Date(b.timestamp || 0).getTime();
        return timeB - timeA;
      });

      // Paginate the results
      const startIndex = (page - 1) * perPage;
      const endIndex = startIndex + perPage;
      const paginatedBooks = allBooks.slice(startIndex, endIndex);

      setBooks(paginatedBooks);
      setTotalBooks(allBooks.length);
    } catch (err: any) {
      setError(err.response?.data?.detail || t('categories.failedToLoadBooks'));
    } finally {
      setLoadingBooks(false);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center">{t('common.loading')}</div>
      </div>
    );
  }

  if (error || !category) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error || t('categories.notFound')}
        </div>
        <Link to="/categories" className="text-blue-600 hover:underline mt-4 inline-block">
          {t('categories.backToList')}
        </Link>
      </div>
    );
  }

  const totalPages = Math.ceil(totalBooks / perPage);

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <Link
          to="/categories"
          className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          {t('categories.backToList')}
        </Link>

        <div className="flex items-start gap-4">
          <FolderTree className="w-10 h-10 text-blue-600 mt-1" />
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-gray-800 mb-2">{category.name}</h1>
            {category.description && (
              <p className="text-gray-600 mb-4">{category.description}</p>
            )}

            {/* Tags */}
            {category.tags.length > 0 && (
              <div className="mb-4">
                <div className="flex items-center gap-2 mb-2">
                  <TagIcon className="w-4 h-4 text-gray-500" />
                  <span className="text-sm font-medium text-gray-600">
                    {t('categories.includedTags')}:
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {category.tags.map((tag) => (
                    <Link
                      key={tag.id}
                      to={`/?tag=${encodeURIComponent(tag.name)}`}
                      className="bg-blue-50 text-blue-700 px-3 py-1 rounded-full text-sm hover:bg-blue-100 transition-colors"
                    >
                      {tag.name}
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {category.book_count !== undefined && (
              <p className="text-gray-600">
                {t('categories.totalBooks', { count: category.book_count })}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Books Grid */}
      {loadingBooks ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">{t('common.loading')}</p>
        </div>
      ) : books.length === 0 ? (
        <div className="bg-gray-50 rounded-lg p-8 text-center">
          <p className="text-gray-500">{t('categories.noBooksFound')}</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
            {books.map((book) => (
              <BookCard key={book.id} book={book} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-center items-center gap-2 mt-8">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {t('common.previous')}
              </button>

              <span className="px-4 py-2 text-gray-700">
                {t('common.pageOfTotal', { page, total: totalPages })}
              </span>

              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {t('common.next')}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
