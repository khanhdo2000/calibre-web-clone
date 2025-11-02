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
  const coverUrl = book.has_cover ? booksApi.getCoverUrl(book.id) : null;

  return (
    <div className="flex flex-col">
      <Link to={`/book/${book.id}`}>
        <div className="aspect-[2/3] bg-gray-200 relative overflow-hidden rounded mb-3">
          {coverUrl ? (
            <img
              src={coverUrl}
              alt={book.title}
              className="w-full h-full object-cover"
              loading="lazy"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <BookOpen className="w-16 h-16 text-gray-400" />
            </div>
          )}
        </div>
      </Link>

      <Link to={`/book/${book.id}`}>
        <h3 className="font-semibold text-base mb-2 line-clamp-2 hover:text-blue-600 leading-snug">
          {book.title}
        </h3>
      </Link>

      <p className="text-sm text-gray-600 leading-snug">
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
