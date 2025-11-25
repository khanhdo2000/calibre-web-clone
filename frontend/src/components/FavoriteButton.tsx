import { Heart } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useFavorites } from '@/contexts/FavoritesContext';
import { useAuth } from '@/contexts/AuthContext';
import { useState } from 'react';

interface FavoriteButtonProps {
  bookId: number;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export function FavoriteButton({ bookId, className = '', size = 'md', showLabel = false }: FavoriteButtonProps) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { isFavorite, toggleFavorite } = useFavorites();
  const [isAnimating, setIsAnimating] = useState(false);

  const sizeClasses = {
    sm: 'w-5 h-5',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };

  const buttonSizeClasses = {
    sm: 'min-w-[44px] min-h-[44px]', // Minimum touch target size
    md: 'min-w-[48px] min-h-[48px]',
    lg: 'min-w-[56px] min-h-[56px]',
  };

  if (!user) {
    return null;
  }

  const handleClick = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    setIsAnimating(true);
    try {
      await toggleFavorite(bookId);
    } catch (error) {
      console.error('Failed to toggle favorite:', error);
    } finally {
      setTimeout(() => setIsAnimating(false), 300);
    }
  };

  const isFav = isFavorite(bookId);
  const ariaLabel = isFav ? t('favorites.removeFromFavorites') : t('favorites.addToFavorites');

  return (
    <button
      onClick={handleClick}
      className={`flex items-center justify-center gap-2 transition-all duration-200 hover:scale-105 active:scale-95 ${
        isAnimating ? 'scale-110' : ''
      } ${buttonSizeClasses[size]} ${className}`}
      aria-label={ariaLabel}
      title={ariaLabel}
    >
      <Heart
        className={`${sizeClasses[size]} transition-colors ${
          isFav
            ? 'fill-red-500 text-red-500'
            : 'text-gray-400 hover:text-red-400'
        }`}
      />
      {showLabel && (
        <span className={`text-sm font-medium ${isFav ? 'text-red-500' : 'text-gray-700'}`}>
          {isFav ? t('favorites.removeFromFavorites') : t('favorites.addToFavorites')}
        </span>
      )}
    </button>
  );
}
