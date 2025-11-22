import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { BookCard } from '../components/BookCard';

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

export function SelectBooksPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const deviceKey = searchParams.get('key');

  const [books, setBooks] = useState<Book[]>([]);
  const [selectedBookIds, setSelectedBookIds] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (!deviceKey) {
      navigate('/pair');
      return;
    }

    fetchBooks();
  }, [deviceKey, navigate]);

  const fetchBooks = async () => {
    setLoading(true);
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

  const toggleBook = (bookId: number) => {
    const newSelected = new Set(selectedBookIds);
    if (newSelected.has(bookId)) {
      newSelected.delete(bookId);
    } else {
      newSelected.add(bookId);
    }
    setSelectedBookIds(newSelected);
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

      {/* Books Grid */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        {books.length === 0 ? (
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
