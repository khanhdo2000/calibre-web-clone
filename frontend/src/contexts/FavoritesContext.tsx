import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { favoritesApi, Favorite } from '@/services/api';
import { useAuth } from './AuthContext';

interface FavoritesContextType {
  favorites: Set<number>;
  loading: boolean;
  toggleFavorite: (bookId: number) => Promise<void>;
  isFavorite: (bookId: number) => boolean;
  refreshFavorites: () => Promise<void>;
}

const FavoritesContext = createContext<FavoritesContextType | undefined>(undefined);

export function FavoritesProvider({ children }: { children: ReactNode }) {
  const [favorites, setFavorites] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(false);
  const { user } = useAuth();

  // Load favorites when user logs in
  useEffect(() => {
    if (user) {
      loadFavorites();
    } else {
      setFavorites(new Set());
    }
  }, [user]);

  const loadFavorites = async () => {
    setLoading(true);
    try {
      const data = await favoritesApi.getFavorites();
      const favoriteIds = new Set(data.map((fav: Favorite) => fav.book_id));
      setFavorites(favoriteIds);
    } catch (error) {
      console.error('Error loading favorites:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleFavorite = async (bookId: number) => {
    if (!user) {
      throw new Error('Must be logged in to favorite books');
    }

    const wasFavorite = favorites.has(bookId);

    // Optimistic update
    const newFavorites = new Set(favorites);
    if (wasFavorite) {
      newFavorites.delete(bookId);
    } else {
      newFavorites.add(bookId);
    }
    setFavorites(newFavorites);

    try {
      if (wasFavorite) {
        await favoritesApi.removeFavorite(bookId);
      } else {
        await favoritesApi.addFavorite(bookId);
      }
    } catch (error) {
      // Revert on error
      setFavorites(favorites);
      console.error('Error toggling favorite:', error);
      throw error;
    }
  };

  const isFavorite = (bookId: number): boolean => {
    return favorites.has(bookId);
  };

  const refreshFavorites = async () => {
    if (user) {
      await loadFavorites();
    }
  };

  return (
    <FavoritesContext.Provider value={{ favorites, loading, toggleFavorite, isFavorite, refreshFavorites }}>
      {children}
    </FavoritesContext.Provider>
  );
}

export function useFavorites() {
  const context = useContext(FavoritesContext);
  if (context === undefined) {
    throw new Error('useFavorites must be used within a FavoritesProvider');
  }
  return context;
}
