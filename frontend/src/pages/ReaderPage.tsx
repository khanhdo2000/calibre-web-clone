import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, ChevronLeft, ChevronRight, List, X } from 'lucide-react';
import { booksApi } from '@/services/api';
import type { BookDetail } from '@/types';
// @ts-ignore - epubjs types may not be available
import ePub from 'epubjs';

interface TocItem {
  id: string;
  href: string;
  label: string;
  subitems?: TocItem[];
}

export function ReaderPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const [book, setBook] = useState<BookDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showToc, setShowToc] = useState(false);
  const [toc, setToc] = useState<TocItem[]>([]);
  const viewerRef = useRef<HTMLDivElement>(null);
  const renditionRef = useRef<any>(null);
  const epubBookRef = useRef<any>(null);

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
        
        // Fetch EPUB as blob/arraybuffer so EPUB.js can unpack it client-side
        // This prevents EPUB.js from making additional HTTP requests for internal files
        const response = await fetch(bookUrl);
        if (!response.ok) {
          throw new Error(`Failed to load EPUB: ${response.statusText}`);
        }
        const epubBlob = await response.blob();
        
        // Pass blob to EPUB.js instead of URL
        const epubBook = ePub(epubBlob);
        epubBookRef.current = epubBook;
        
        // Load table of contents
        epubBook.ready.then(() => {
          return epubBook.loaded.navigation;
        }).then((nav: any) => {
          if (nav && nav.toc && nav.toc.length > 0) {
            const tocItems = nav.toc.map((item: any) => ({
              id: item.id || '',
              href: item.href || '',
              label: item.label || '',
              subitems: item.subitems?.map((subitem: any) => ({
                id: subitem.id || '',
                href: subitem.href || '',
                label: subitem.label || '',
              })),
            }));
            setToc(tocItems);
          }
        }).catch((err: any) => {
          console.warn('Failed to load table of contents:', err);
        });
        
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

  const navigateToTocItem = (href: string) => {
    if (renditionRef.current && href) {
      renditionRef.current.display(href);
      setShowToc(false);
    }
  };

  const renderTocItems = (items: TocItem[], level = 0) => {
    return items.map((item) => (
      <div key={item.id || item.href} className={level > 0 ? 'ml-4' : ''}>
        <button
          onClick={() => navigateToTocItem(item.href)}
          className="w-full text-left px-3 py-2 hover:bg-gray-100 rounded text-sm"
          style={{ paddingLeft: `${(level + 1) * 0.75}rem` }}
        >
          {item.label}
        </button>
        {item.subitems && item.subitems.length > 0 && (
          <div className="mt-1">
            {renderTocItems(item.subitems, level + 1)}
          </div>
        )}
      </div>
    ));
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
            onClick={() => setShowToc(!showToc)}
            className="p-2 hover:bg-gray-100 rounded"
            title={showToc ? t('reader.hideToc') : t('reader.showToc')}
          >
            {showToc ? <X className="w-5 h-5" /> : <List className="w-5 h-5" />}
          </button>
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
      <div className="flex-1 overflow-hidden flex">
        {/* TOC Sidebar */}
        {showToc && (
          <div className="w-80 bg-white shadow-lg overflow-y-auto border-r">
            <div className="p-4 border-b sticky top-0 bg-white z-10">
              <h2 className="text-lg font-semibold">{t('reader.tableOfContents')}</h2>
            </div>
            <div className="p-2">
              {toc.length > 0 ? (
                <div className="space-y-1">
                  {renderTocItems(toc)}
                </div>
              ) : (
                <p className="text-gray-500 text-sm px-3 py-2">
                  {t('reader.noTocAvailable')}
                </p>
              )}
            </div>
          </div>
        )}
        <div className="flex-1 overflow-hidden">
          <div
            ref={viewerRef}
            className="w-full h-full max-w-4xl mx-auto bg-white shadow-lg"
          />
        </div>
      </div>

      {/* Footer hint */}
      <div className="bg-white border-t px-4 py-2 text-center text-sm text-gray-500">
        {t('reader.navigateHint')}
      </div>
    </div>
  );
}
