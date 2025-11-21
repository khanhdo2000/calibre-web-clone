import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { booksApi, metadataApi } from '@/services/api';
import { BookCard } from '@/components/BookCard';
import { Pagination } from '@/components/Pagination';
import { SortButtons } from '@/components/SortButtons';
import type { BookListResponse } from '@/types';

export function BooksPage() {
  const { t } = useTranslation();
  const params = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [data, setData] = useState<BookListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterTitle, setFilterTitle] = useState<string>(t('home.recentlyAdded'));

  // Extract route parameters
  const page = parseInt(params.page || '1');
  const perPage = 60;

  // Check for query parameters first (tag name or publisher name)
  const tagName = searchParams.get('tag');
  const publisherName = searchParams.get('publisher');

  // Determine data type from URL path
  const pathname = window.location.pathname;
  let dataType: string | null = null;
  if (pathname.startsWith('/category/')) {
    dataType = 'category';
  } else if (pathname.startsWith('/author/')) {
    dataType = 'author';
  } else if (pathname.startsWith('/publisher/')) {
    dataType = 'publisher';
  } else if (pathname.startsWith('/series/')) {
    dataType = 'series';
  }

  const itemId = params.id ? parseInt(params.id) : undefined;
  // Get sort_param from route params or query params, default to 'new'
  const sortParamValue = params.sort_param || searchParams.get('sort') || 'new';
  const sortParam = sortParamValue as 'new' | 'old' | 'abc' | 'zyx' | 'authaz' | 'authza' | 'pubnew' | 'pubold' | 'seriesasc' | 'seriesdesc';

  // Map route data type to filter type
  const authorId = dataType === 'author' ? itemId : undefined;
  const tagId = dataType === 'category' ? itemId : undefined;
  const publisherId = dataType === 'publisher' ? itemId : undefined;
  const seriesId = dataType === 'series' ? itemId : undefined;

  useEffect(() => {
    loadBooks();
    loadFilterTitle();
  }, [page, authorId, tagId, publisherId, seriesId, sortParam, tagName, publisherName]);

  const loadFilterTitle = async () => {
    if (authorId) {
      try {
        const authors = await metadataApi.getAuthors();
        const author = authors.find(a => a.id === authorId);
        setFilterTitle(author ? t('home.booksByAuthor', { author: author.name }) : t('home.booksByAuthorDefault'));
      } catch (err) {
        setFilterTitle(t('home.booksByAuthorDefault'));
      }
    } else if (tagId !== undefined) {
      if (tagId === -1) {
        setFilterTitle(t('home.categoryNone'));
      } else {
        try {
          const tags = await metadataApi.getTags();
          const tag = tags.find(c => c.id === tagId);
          setFilterTitle(tag ? t('home.category', { name: tag.name }) : t('home.categoryDefault'));
        } catch (err) {
          setFilterTitle(t('home.categoryDefault'));
        }
      }
    } else if (publisherId) {
      try {
        const publishers = await metadataApi.getPublishers();
        const publisher = publishers.find(p => p.id === publisherId);
        setFilterTitle(publisher ? t('home.booksFromPublisher', { publisher: publisher.name }) : t('home.booksFromPublisherDefault'));
      } catch (err) {
        setFilterTitle(t('home.booksFromPublisherDefault'));
      }
    } else if (seriesId) {
      try {
        const series = await metadataApi.getSeries();
        const s = series.find(s => s.id === seriesId);
        setFilterTitle(s ? t('home.series', { name: s.name }) : t('home.seriesDefault'));
      } catch (err) {
        setFilterTitle(t('home.seriesDefault'));
      }
    } else if (tagName) {
      setFilterTitle(t('home.category', { name: tagName }));
    } else if (publisherName) {
      setFilterTitle(t('home.booksFromPublisher', { publisher: publisherName }));
    } else {
      setFilterTitle(t('home.recentlyAdded'));
    }
  };

  const loadBooks = async () => {
    setLoading(true);
    setError(null);

    try {
      // If we have tag or publisher names, look up their IDs
      let resolvedTagId = tagId;
      let resolvedPublisherId = publisherId;

      if (tagName && !tagId) {
        try {
          const tags = await metadataApi.getTags();
          const tag = tags.find(c => c.name.toLowerCase() === tagName.toLowerCase());
          resolvedTagId = tag?.id;
        } catch (err) {
          console.error('Failed to resolve tag name:', err);
        }
      }

      if (publisherName && !publisherId) {
        try {
          const publishers = await metadataApi.getPublishers();
          const publisher = publishers.find(p => p.name.toLowerCase() === publisherName.toLowerCase());
          resolvedPublisherId = publisher?.id;
        } catch (err) {
          console.error('Failed to resolve publisher name:', err);
        }
      }

      const response = await booksApi.getBooks({
        page,
        per_page: perPage,
        sort_param: sortParam,
        author_id: authorId,
        publisher_id: resolvedPublisherId,
        series_id: seriesId,
        tag_id: resolvedTagId,
      });
      setData(response);
    } catch (err) {
      setError(t('home.failedToLoad'));
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handlePageChange = (newPage: number) => {
    if (dataType && itemId) {
      // Navigate with route parameters
      navigate(`/${dataType}/${sortParam}/${itemId}/page/${newPage}`);
    } else {
      // Build query parameters
      const queryParams = new URLSearchParams();
      if (sortParam !== 'new') {
        queryParams.set('sort', sortParam);
      }
      if (tagName) {
        queryParams.set('tag', tagName);
      }
      if (publisherName) {
        queryParams.set('publisher', publisherName);
      }
      const queryString = queryParams.toString();
      const query = queryString ? `?${queryString}` : '';
      navigate(newPage > 1 ? `/page/${newPage}${query}` : `/${query}`);
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">{t('home.loadingBooks')}</p>
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
          <p className="text-xl font-semibold mb-2">{t('home.noBooksFound')}</p>
          <p>{t('home.libraryEmpty')}</p>
        </div>
      </div>
    );
  }

  const totalPages = Math.ceil(data.total / perPage);

  return (
    <div>
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">{filterTitle}</h1>
          <p className="text-gray-600 mt-1">
            {t('home.showing', {
              start: (page - 1) * perPage + 1,
              end: Math.min(page * perPage, data.total),
              total: data.total
            })}
          </p>
        </div>
        <SortButtons currentSort={sortParam} showSeriesSort={dataType === 'series'} />
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
