import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, ChevronLeft, ChevronRight } from 'lucide-react';
import { booksApi } from '@/services/api';
import type { BookDetail } from '@/types';
// @ts-ignore - epubjs types may not be available
import ePub from 'epubjs';

export function ReaderPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const [book, setBook] = useState<BookDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const viewerRef = useRef<HTMLDivElement>(null);
  const renditionRef = useRef<any>(null);

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

      if (!data.file_formats.includes('EPUB')) {
        setError(t('reader.notAvailable'));
        setLoading(false);
        return;
      }

      // Initialize epub reader
      if (viewerRef.current) {
        const bookUrl = booksApi.getReadUrl(bookId, 'epub');
        const epubBook = ePub(bookUrl);
        const rendition = epubBook.renderTo(viewerRef.current, {
          width: '100%',
          height: '100%',
          spread: 'none',
        });

        rendition.display();
        renditionRef.current = rendition;

        // Navigation with arrow keys
        document.addEventListener('keydown', handleKeyPress);
      }

      setLoading(false);
    } catch (err) {
      setError(t('reader.failedToLoad'));
      console.error(err);
      setLoading(false);
    }

    return () => {
      document.removeEventListener('keydown', handleKeyPress);
    };
  };

  const handleKeyPress = (e: KeyboardEvent) => {
    if (renditionRef.current) {
      if (e.key === 'ArrowRight') {
        renditionRef.current.next();
      } else if (e.key === 'ArrowLeft') {
        renditionRef.current.prev();
      }
    }
  };

  const goNext = () => {
    if (renditionRef.current) {
      renditionRef.current.next();
    }
  };

  const goPrev = () => {
    if (renditionRef.current) {
      renditionRef.current.prev();
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">{t('reader.loading')}</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-xl font-semibold mb-4 text-red-600">{error}</p>
          <Link
            to={`/book/${id}`}
            className="text-blue-600 hover:underline inline-flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            {t('reader.backToDetails')}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-gray-100 flex flex-col">
      {/* Header */}
      <div className="bg-white shadow-sm px-4 py-3 flex items-center justify-between">
        <Link
          to={`/book/${id}`}
          className="text-blue-600 hover:text-blue-700 inline-flex items-center gap-2"
        >
          <ArrowLeft className="w-5 h-5" />
          {t('common.back')}
        </Link>

        <h1 className="text-lg font-semibold text-gray-800 truncate max-w-md">
          {book?.title}
        </h1>

        <div className="flex gap-2">
          <button
            onClick={goPrev}
            className="p-2 hover:bg-gray-100 rounded"
            title={t('reader.previousPage')}
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <button
            onClick={goNext}
            className="p-2 hover:bg-gray-100 rounded"
            title={t('reader.nextPage')}
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Reader */}
      <div className="flex-1 overflow-hidden">
        <div
          ref={viewerRef}
          className="w-full h-full max-w-4xl mx-auto bg-white shadow-lg"
        />
      </div>

      {/* Footer hint */}
      <div className="bg-white border-t px-4 py-2 text-center text-sm text-gray-500">
        {t('reader.navigateHint')}
      </div>
    </div>
  );
}
