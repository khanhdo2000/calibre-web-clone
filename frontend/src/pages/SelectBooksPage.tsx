import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { BookCard } from '../components/BookCard';
import { categoryGroupsApi } from '@/services/api';
import type { CategoryGroup, Book as BookType } from '@/types';
import { FolderTree, ChevronRight, Newspaper } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

interface Book {
  id: number;
  title: string;
  authors: Array<{ id: number; name: string }>;
  tags: Array<{ id: number; name: string }>;
  has_cover: boolean;
  path: string;
  file_formats: string[];
}

interface CategoryWithBooks {
  category: CategoryGroup;
  books: BookType[];
}

interface RssGeneratedBook {
  id: number;
  feed_id: number;
  title: string;
  filename: string;
  file_size: number;
  mobi_filename: string | null;
  mobi_file_size: number | null;
  article_count: number;
  generation_date: string;
}

export function SelectBooksPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const deviceKey = searchParams.get('key');

  const [books, setBooks] = useState<Book[]>([]);
  const [categoriesWithBooks, setCategoriesWithBooks] = useState<CategoryWithBooks[]>([]);
  const [rssBooks, setRssBooks] = useState<RssGeneratedBook[]>([]);
  const [showCategories, setShowCategories] = useState(true);
  const [expandedCategories, setExpandedCategories] = useState<Set<number>>(new Set());
  const [selectedBookIds, setSelectedBookIds] = useState<Set<number>>(new Set());
  const [initialLoad, setInitialLoad] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [sending, setSending] = useState(false);
  const booksPerCategory = 12;

  useEffect(() => {
    if (!deviceKey) {
      navigate('/pair');
      return;
    }

    if (initialLoad) {
      // On initial load, show categories and load RSS books
      loadCategoriesWithBooks();
      loadRssBooks();
      setInitialLoad(false);
    }
  }, [deviceKey, navigate, initialLoad]);

  const loadRssBooks = async () => {
    try {
      const response = await axios.get(`${API_URL}/rss/books`, {
        params: { limit: 100 } // Fetch more to ensure we get all feeds
      });

      // Group by feed_id and keep only the latest book from each feed
      const booksByFeed = new Map<number, RssGeneratedBook>();

      response.data.forEach((book: RssGeneratedBook) => {
        const existing = booksByFeed.get(book.feed_id);
        if (!existing || new Date(book.generation_date) > new Date(existing.generation_date)) {
          booksByFeed.set(book.feed_id, book);
        }
      });

      // Convert map to array and sort by generation date (newest first)
      const latestBooks = Array.from(booksByFeed.values())
        .sort((a, b) => new Date(b.generation_date).getTime() - new Date(a.generation_date).getTime());

      setRssBooks(latestBooks);
    } catch (err) {
      console.error('Error loading RSS books:', err);
    }
  };


  const loadCategoriesWithBooks = async () => {
    setLoading(true);
    setError('');
    setShowCategories(true);
    try {
      // Fetch all categories
      const categoriesData = await categoryGroupsApi.getAll();
      const categories = categoriesData.categories;

      if (categories.length === 0) {
        setCategoriesWithBooks([]);
        setLoading(false);
        return;
      }

      // Fetch books for each category in parallel
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
      const categoriesWithBooksData: CategoryWithBooks[] = [];
      results.forEach(result => {
        if (result) {
          categoriesWithBooksData.push(result);
        }
      });

      setCategoriesWithBooks(categoriesWithBooksData);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Tải danh mục thất bại');
    } finally {
      setLoading(false);
    }
  };

  const fetchBooks = async () => {
    setLoading(true);
    setShowCategories(false);
    try {
      const params: any = {
        page: 1,
        per_page: 100,
        sort_by: 'timestamp',
        order: 'desc',
      };

      // Add search_query if user has typed something
      if (searchQuery.trim()) {
        params.search_query = searchQuery.trim();
      }

      const response = await axios.get(`${API_URL}/books/`, {
        params,
      });
      setBooks(response.data.books || []);
      setLoading(false);
    } catch (err) {
      console.error('Error fetching books:', err);
      setError(searchQuery ? 'Tìm kiếm thất bại' : 'Tải sách thất bại');
      setLoading(false);
    }
  };

  const toggleCategory = (categoryId: number) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(categoryId)) {
      newExpanded.delete(categoryId);
    } else {
      newExpanded.add(categoryId);
    }
    setExpandedCategories(newExpanded);
  };

  const toggleBook = (bookId: number) => {
    const newSelected = new Set(selectedBookIds);
    if (newSelected.has(bookId)) {
      newSelected.delete(bookId);
    } else {
      newSelected.add(bookId);
    }
    setSelectedBookIds(newSelected);
  };

  const toggleRssBook = (rssBookId: number) => {
    // Use negative ID to distinguish RSS books from regular books
    const bookId = -rssBookId;
    toggleBook(bookId);
  };

  const sendToKindle = async () => {
    if (selectedBookIds.size === 0) {
      setError('Vui lòng chọn ít nhất một cuốn sách');
      return;
    }

    setSending(true);
    setError('');

    try {
      await axios.post(`${API_URL}/kindle-pair/select-books`, {
        device_key: deviceKey,
        book_ids: Array.from(selectedBookIds),
      });

      // Show success message
      alert(`Đã gửi thành công ${selectedBookIds.size} sách đến Kindle của bạn!`);
      setSelectedBookIds(new Set());
    } catch (err) {
      console.error('Error sending books:', err);
      if (axios.isAxiosError(err) && err.response?.status === 404) {
        setError('Phiên đã hết hạn. Vui lòng ghép nối lại.');
        setTimeout(() => navigate('/pair'), 2000);
      } else {
        setError('Gửi sách thất bại. Vui lòng thử lại.');
      }
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-lg">Đang tải sách...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold">Chọn sách cho Kindle</h1>
              <p className="text-sm text-gray-600">
                Thiết bị: <span className="font-mono font-semibold">{deviceKey}</span>
              </p>
            </div>
            <button
              onClick={() => navigate('/pair')}
              className="text-sm text-blue-600 hover:underline"
            >
              Đổi thiết bị
            </button>
          </div>

          {/* Search Bar */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              fetchBooks();
            }}
            className="flex gap-3"
          >
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Tìm sách hoặc tác giả..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery('');
                  loadCategoriesWithBooks();
                }}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Xóa
              </button>
            )}
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
            >
              {loading ? 'Đang tìm...' : 'Tìm kiếm'}
            </button>
          </form>

          {error && (
            <div className="mt-3 text-red-600 text-sm bg-red-50 p-3 rounded">
              {error}
            </div>
          )}
        </div>
      </div>

      {/* Books Grid or Categories */}
      <div className={showCategories ? "" : "max-w-7xl mx-auto px-4 py-6"}>
        {showCategories ? (
          // Category View - Edge to Edge Horizontal Scroll
          <div>
            {/* RSS News Section */}
            {rssBooks.length > 0 && (
              <div className="md:bg-white md:rounded-lg md:shadow-sm md:border md:border-gray-200 md:p-6 md:mx-4 mb-8 md:mb-12">
                <div className="flex items-center gap-3 mb-6 px-4 md:px-0">
                  <Newspaper className="w-6 h-6 text-orange-600" />
                  <div>
                    <h2 className="text-xl md:text-2xl font-bold text-gray-800">
                      Tin tức RSS
                    </h2>
                    <p className="text-gray-600 text-xs md:text-sm mt-1">
                      Tự động tạo từ nguồn RSS
                    </p>
                  </div>
                </div>

                <div className="px-4 md:px-0">
                  <div className="space-y-3">
                    {rssBooks.map((book) => {
                      const isSelected = selectedBookIds.has(-book.id);
                      return (
                        <div
                          key={book.id}
                          onClick={() => toggleRssBook(book.id)}
                          className={`bg-gray-50 rounded-lg p-4 transition-all border-2 cursor-pointer relative ${
                            isSelected
                              ? 'border-blue-500 bg-blue-50'
                              : 'border-gray-200 hover:bg-gray-100 hover:border-gray-300'
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <div className={`flex-shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center ${
                              isSelected
                                ? 'bg-blue-600 border-blue-600'
                                : 'border-gray-300'
                            }`}>
                              {isSelected && (
                                <span className="text-white font-bold text-sm">✓</span>
                              )}
                            </div>
                            <div className="flex-1 min-w-0">
                              <h3 className="font-semibold text-gray-900 truncate">
                                {book.title}
                              </h3>
                              <div className="flex flex-wrap items-center gap-2 mt-1 text-sm text-gray-600">
                                <span>{book.article_count} bài viết</span>
                                <span className="text-gray-400">•</span>
                                <span>{new Date(book.generation_date).toLocaleDateString('vi-VN')}</span>
                                {book.mobi_filename && (
                                  <>
                                    <span className="text-gray-400">•</span>
                                    <span className="text-green-600 font-medium">MOBI</span>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            {categoriesWithBooks.length === 0 ? (
              <div className="text-center text-gray-500 py-12 px-4">
                Không có danh mục nào.
              </div>
            ) : (
              <div className="space-y-8 md:space-y-12">
                {categoriesWithBooks.map(({ category, books: categoryBooks }) => {
                const isExpanded = expandedCategories.has(category.id);

                return (
                  <div key={category.id} className="md:bg-white md:rounded-lg md:shadow-sm md:border md:border-gray-200 md:p-6 md:mx-4">
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
                      <button
                        onClick={() => toggleCategory(category.id)}
                        className="flex items-center gap-1 md:gap-2 text-blue-600 hover:text-blue-700 font-medium transition-colors text-sm md:text-base whitespace-nowrap"
                      >
                        <span className="hidden sm:inline">
                          {isExpanded ? 'Thu gọn' : `Xem tất cả (${categoryBooks.length})`}
                        </span>
                        <ChevronRight className={`w-4 h-4 md:w-5 md:h-5 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                      </button>
                    </div>

                    {/* Books - Horizontal Scroll or Grid */}
                    {isExpanded ? (
                      // Expanded: Grid View
                      <div className="px-4 md:px-0">
                        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3 md:gap-4">
                          {categoryBooks.map((book) => {
                            const isSelected = selectedBookIds.has(book.id);
                            return (
                              <div
                                key={book.id}
                                onClick={(e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
                                  toggleBook(book.id);
                                }}
                                className={`relative cursor-pointer transition-all ${
                                  isSelected
                                    ? 'ring-4 ring-blue-500 ring-offset-2 scale-95'
                                    : 'hover:shadow-lg'
                                }`}
                                style={{ pointerEvents: 'auto' }}
                              >
                                <div style={{ pointerEvents: 'none' }}>
                                  <BookCard book={book} />
                                </div>
                                {isSelected && (
                                  <div className="absolute top-2 right-2 bg-blue-600 text-white rounded-full w-8 h-8 flex items-center justify-center font-bold shadow-lg">
                                    ✓
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ) : (
                      // Collapsed: Horizontal Scroll
                      <div className="relative md:-mx-2">
                        <div className="overflow-x-auto scrollbar-hide pb-2">
                          <div className="flex gap-3 pl-4 md:gap-4 md:px-2" style={{ width: 'max-content' }}>
                            {categoryBooks.map((book) => {
                              const isSelected = selectedBookIds.has(book.id);
                              return (
                                <div
                                  key={book.id}
                                  onClick={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    toggleBook(book.id);
                                  }}
                                  className={`w-32 md:w-40 flex-shrink-0 relative cursor-pointer transition-all ${
                                    isSelected
                                      ? 'ring-4 ring-blue-500 ring-offset-2 scale-95'
                                      : 'hover:shadow-lg'
                                  }`}
                                  style={{ pointerEvents: 'auto' }}
                                >
                                  <div style={{ pointerEvents: 'none' }}>
                                    <BookCard book={book} />
                                  </div>
                                  {isSelected && (
                                    <div className="absolute top-2 right-2 bg-blue-600 text-white rounded-full w-8 h-8 flex items-center justify-center font-bold shadow-lg">
                                      ✓
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            )}
          </div>
        ) : (
          // Search Results View (original grid)
          books.length === 0 ? (
            <div className="text-center text-gray-500 py-12">
              {searchQuery ? 'Không tìm thấy sách phù hợp.' : 'Không có sách.'}
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
              {books.map((book) => {
                const isSelected = selectedBookIds.has(book.id);
                return (
                  <div
                    key={book.id}
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      toggleBook(book.id);
                    }}
                    className={`relative cursor-pointer transition-all ${
                      isSelected
                        ? 'ring-4 ring-blue-500 ring-offset-2 scale-95'
                        : 'hover:shadow-lg'
                    }`}
                    style={{ pointerEvents: 'auto' }}
                  >
                    <div style={{ pointerEvents: 'none' }}>
                      <BookCard book={book} />
                    </div>
                    {isSelected && (
                      <div className="absolute top-2 right-2 bg-blue-600 text-white rounded-full w-8 h-8 flex items-center justify-center font-bold shadow-lg">
                        ✓
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )
        )}
      </div>

      {/* Fixed Footer with Selection Count */}
      {selectedBookIds.size > 0 && (
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t shadow-lg">
          <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
            <div className="text-lg font-semibold">
              Đã chọn {selectedBookIds.size} sách
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setSelectedBookIds(new Set())}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Xóa
              </button>
              <button
                onClick={sendToKindle}
                disabled={sending}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-300 transition-colors"
              >
                {sending ? 'Đang gửi...' : 'Gửi đến Kindle'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
