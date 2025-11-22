import { useTranslation } from 'react-i18next';
import { Book } from '@/types';
import { booksApi } from '@/services/api';
import { BookOpen } from 'lucide-react';
import { Link } from 'react-router-dom';

interface BookCardProps {
  book: Book;
}

export function BookCard({ book }: BookCardProps) {
  const { t } = useTranslation();
  // For list view, prefer thumbnail for better performance, fallback to full-size or API endpoint
  const coverUrl = book.cover_thumb_url || book.cover_url || (book.has_cover ? booksApi.getCoverUrl(book.id) : null);

  return (
    <div className="flex flex-col">
      <Link to={`/book/${book.id}`}>
        <div className="aspect-[2/3] bg-gray-200 relative overflow-hidden rounded mb-2 md:mb-3">
          {coverUrl ? (
            <img
              src={coverUrl}
              alt={book.title}
              className="w-full h-full object-cover"
              loading="lazy"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <BookOpen className="w-12 h-12 md:w-16 md:h-16 text-gray-400" />
            </div>
          )}
        </div>
      </Link>

      <Link to={`/book/${book.id}`}>
        <h3 className="font-semibold text-sm md:text-base mb-1 md:mb-2 line-clamp-2 hover:text-blue-600 leading-snug">
          {book.title}
        </h3>
      </Link>

      <p className="text-xs md:text-sm text-gray-600 leading-snug line-clamp-1">
        {book.authors.length > 0 ? (
          book.authors.map((author, index) => (
            <span key={author.id}>
              <Link
                to={`/author/stored/${author.id}`}
                className="hover:text-blue-600 hover:underline"
                onClick={(e) => e.stopPropagation()}
              >
                {author.name}
              </Link>
              {index < book.authors.length - 1 && ', '}
            </span>
          ))
        ) : (
          t('book.card.unknownAuthor')
        )}
      </p>
    </div>
  );
}
