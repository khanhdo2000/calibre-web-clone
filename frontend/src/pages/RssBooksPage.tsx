import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { rssBooksApi, type RssFeed, type RssGeneratedBook } from '@/services/api';
import { Newspaper, Download, Calendar, FileText, RefreshCw, Send } from 'lucide-react';

export function RssBooksPage() {
  const { t } = useTranslation();
  const [feeds, setFeeds] = useState<RssFeed[]>([]);
  const [books, setBooks] = useState<RssGeneratedBook[]>([]);
  const [selectedFeed, setSelectedFeed] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState<number | null>(null);
  const [sending, setSending] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    loadBooks();
  }, [selectedFeed]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [feedsData, booksData] = await Promise.all([
        rssBooksApi.getFeeds(),
        rssBooksApi.getBooks()
      ]);
      setFeeds(feedsData);
      setBooks(booksData);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load RSS books');
    } finally {
      setLoading(false);
    }
  };

  const loadBooks = async () => {
    try {
      const booksData = await rssBooksApi.getBooks(selectedFeed || undefined);
      setBooks(booksData);
    } catch (err: any) {
      console.error('Failed to load books:', err);
    }
  };

  const handleGenerate = async (feedId: number) => {
    setGenerating(feedId);
    setError(null);
    setSuccessMessage(null);
    try {
      await rssBooksApi.generateFeed(feedId);
      await loadBooks();
      setSuccessMessage('EPUB đã được tạo thành công!');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate EPUB');
    } finally {
      setGenerating(null);
    }
  };

  const handleSendToKindle = async (bookId: number, format: 'epub' | 'mobi' = 'epub') => {
    setSending(bookId);
    setError(null);
    setSuccessMessage(null);
    try {
      const result = await rssBooksApi.sendToKindle(bookId, format);
      setSuccessMessage(result.message);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Không thể gửi đến Kindle';
      setError(errorMsg);
    } finally {
      setSending(null);
    }
  };

  const formatFileSize = (bytes: number | null) => {
    if (!bytes) return '-';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('vi-VN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  };

  const getFeedName = (feedId: number) => {
    const feed = feeds.find(f => f.id === feedId);
    return feed?.name || 'Unknown';
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center">{t('common.loading')}</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Newspaper className="w-8 h-8 text-orange-600" />
        <h1 className="text-3xl font-bold text-gray-800">Tin t&#7913;c h&#224;ng ng&#224;y</h1>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {successMessage && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg mb-6">
          {successMessage}
        </div>
      )}

      {/* Feed Filter */}
      {feeds.length > 0 && (
        <div className="mb-6 flex flex-wrap gap-2">
          <button
            onClick={() => setSelectedFeed(null)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              selectedFeed === null
                ? 'bg-orange-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            T&#7845;t c&#7843;
          </button>
          {feeds.map((feed) => (
            <button
              key={feed.id}
              onClick={() => setSelectedFeed(feed.id)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                selectedFeed === feed.id
                  ? 'bg-orange-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {feed.name}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleGenerate(feed.id);
                }}
                disabled={generating === feed.id}
                className={`p-1 rounded hover:bg-orange-700 ${generating === feed.id ? 'animate-spin' : ''}`}
                title="T&#7841;o EPUB m&#7899;i"
              >
                <RefreshCw className="w-3 h-3" />
              </button>
            </button>
          ))}
        </div>
      )}

      {/* Books List */}
      {books.length === 0 ? (
        <div className="bg-gray-50 rounded-lg p-8 text-center">
          <Newspaper className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">Ch&#432;a c&#243; s&#225;ch RSS n&#224;o &#273;&#432;&#7907;c t&#7841;o</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {books.map((book) => (
            <div
              key={book.id}
              className="bg-white rounded-lg shadow-md p-4 border border-gray-200 hover:shadow-lg transition-all"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-800 mb-2">
                    {book.title}
                  </h3>
                  <div className="flex flex-wrap gap-4 text-sm text-gray-500">
                    <span className="flex items-center gap-1">
                      <Newspaper className="w-4 h-4" />
                      {getFeedName(book.feed_id)}
                    </span>
                    <span className="flex items-center gap-1">
                      <Calendar className="w-4 h-4" />
                      {formatDate(book.generation_date)}
                    </span>
                    <span className="flex items-center gap-1">
                      <FileText className="w-4 h-4" />
                      {book.article_count} b&#224;i vi&#7871;t
                    </span>
                    <span className="text-gray-400">
                      {formatFileSize(book.file_size)}
                    </span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleSendToKindle(book.id, 'epub')}
                    disabled={sending === book.id}
                    className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Gửi EPUB đến Kindle"
                  >
                    <Send className={`w-4 h-4 ${sending === book.id ? 'animate-pulse' : ''}`} />
                    {sending === book.id ? 'Đang gửi...' : 'Kindle'}
                  </button>
                  <a
                    href={rssBooksApi.getDownloadUrl(book.id)}
                    className="flex items-center gap-2 bg-orange-600 text-white px-4 py-2 rounded-lg hover:bg-orange-700 transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    T&#7843;i xu&#7889;ng
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
