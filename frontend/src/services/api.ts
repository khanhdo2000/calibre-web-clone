import axios from 'axios';
import type {
  Book,
  BookDetail,
  BookListResponse,
  SearchResult,
  Author,
  Series,
  Publisher,
  Category,
  FilterOptions,
  CategoryGroup,
  CategoryGroupCreate,
  CategoryGroupUpdate,
  CategoryGroupList,
} from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

// Add auth token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Handle 401 errors and try to refresh token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          // Use axios directly to avoid circular dependency
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, null, {
            params: { refresh_token: refreshToken },
          });
          const { access_token, refresh_token: newRefreshToken } = response.data;
          localStorage.setItem('access_token', access_token);
          localStorage.setItem('refresh_token', newRefreshToken);
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        // Refresh failed, clear tokens and redirect to login
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export const booksApi = {
  getBooks: async (filters?: FilterOptions): Promise<BookListResponse> => {
    const response = await api.get('/books/', { params: filters });
    return response.data;
  },

  getBook: async (id: number): Promise<BookDetail> => {
    const response = await api.get(`/books/${id}`);
    return response.data;
  },

  searchBooks: async (query: string, limit = 50): Promise<SearchResult> => {
    const response = await api.get('/books/search/', { params: { q: query, limit } });
    return response.data;
  },

  getCoverUrl: (bookId: number): string => {
    return `${API_BASE_URL}/files/cover/${bookId}`;
  },

  getDownloadUrl: (bookId: number, format: string): string => {
    return `${API_BASE_URL}/files/download/${bookId}/${format}`;
  },

  getGDriveDirectUrl: (bookId: number, format: string): string => {
    return `${API_BASE_URL}/files/gdrive-link/${bookId}/${format}`;
  },

  getReadUrl: (bookId: number, format: string): string => {
    return `${API_BASE_URL}/files/read/${bookId}/${format}`;
  },

  getRandomBooks: async (limit = 20): Promise<BookListResponse> => {
    const response = await api.get('/books/random/', { params: { limit } });
    return response.data;
  },
};

export const metadataApi = {
  getAuthors: async (): Promise<Author[]> => {
    const response = await api.get('/metadata/authors');
    return response.data;
  },

  getSeries: async (): Promise<Series[]> => {
    const response = await api.get('/metadata/series');
    return response.data;
  },

  getPublishers: async (): Promise<Publisher[]> => {
    const response = await api.get('/metadata/publishers');
    return response.data;
  },

  getTags: async (): Promise<Category[]> => {
    const response = await api.get('/metadata/tags');
    return response.data;
  },
};

export const authApi = {
  login: async (email: string, password: string): Promise<{ access_token: string; refresh_token: string; token_type: string }> => {
    const params = new URLSearchParams();
    // OAuth2PasswordRequestForm uses 'username' field, but we pass email there
    params.append('username', email);
    params.append('password', password);
    const response = await api.post('/auth/login', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return response.data;
  },

  register: async (email: string, password: string, fullName?: string): Promise<{ message: string; email: string }> => {
    const response = await api.post('/auth/register', {
      email,
      password,
      full_name: fullName || null,
    });
    return response.data;
  },

  verifyEmail: async (token: string): Promise<{ message: string; email: string }> => {
    const response = await api.post('/auth/verify-email', { token });
    return response.data;
  },

  resendVerification: async (email: string): Promise<{ message: string }> => {
    const response = await api.post('/auth/resend-verification', { email });
    return response.data;
  },

  getCurrentUser: async (): Promise<{ id: number; email: string; username: string | null; full_name: string | null; is_active: boolean; is_admin: boolean; email_verified: boolean }> => {
    const response = await api.get('/auth/me');
    return response.data;
  },

  refreshToken: async (refreshToken: string): Promise<{ access_token: string; refresh_token: string; token_type: string }> => {
    const response = await axios.post(`${API_BASE_URL}/auth/refresh`, null, {
      params: { refresh_token: refreshToken },
    });
    return response.data;
  },
};

export const kindleEmailApi = {
  sendToKindle: async (bookId: number, kindleEmail?: string): Promise<{ success: boolean; message: string; kindle_email: string }> => {
    const response = await api.post('/kindle-email/send', {
      book_id: bookId,
      ...(kindleEmail && { kindle_email: kindleEmail }),
    });
    return response.data;
  },

  getKindleEmailSettings: async (): Promise<{ kindle_email: string | null }> => {
    const response = await api.get('/kindle-email/settings');
    return response.data;
  },

  updateKindleEmailSettings: async (kindleEmail: string | null): Promise<{ kindle_email: string | null }> => {
    const response = await api.put('/kindle-email/settings', {
      kindle_email: kindleEmail,
    });
    return response.data;
  },

  getEmailServiceStatus: async (): Promise<{ configured: boolean; service_type: string; from_email?: string; smtp_host?: string }> => {
    const response = await api.get('/kindle-email/status');
    return response.data;
  },
};

export const categoryGroupsApi = {
  getAll: async (includeBookCount = true): Promise<CategoryGroupList> => {
    const response = await api.get('/categories/', { params: { include_book_count: includeBookCount } });
    return response.data;
  },

  getById: async (id: number, includeBookCount = true): Promise<CategoryGroup> => {
    const response = await api.get(`/categories/${id}`, { params: { include_book_count: includeBookCount } });
    return response.data;
  },

  create: async (data: CategoryGroupCreate): Promise<CategoryGroup> => {
    const response = await api.post('/categories/', data);
    return response.data;
  },

  update: async (id: number, data: CategoryGroupUpdate): Promise<CategoryGroup> => {
    const response = await api.put(`/categories/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/categories/${id}`);
  },

  getTagIds: async (id: number): Promise<number[]> => {
    const response = await api.get(`/categories/${id}/tags`);
    return response.data;
  },

  getBooks: async (id: number, options?: { page?: number; per_page?: number; sort?: string }): Promise<BookListResponse> => {
    const response = await api.get(`/categories/${id}/books`, { params: options });
    return response.data;
  },

  reorder: async (categories: Array<{ id: number; display_order: number }>): Promise<void> => {
    await api.post('/categories/reorder', { categories });
  },
};

// RSS Books API
export interface RssFeed {
  id: number;
  name: string;
  url: string;
  category: string | null;
  max_articles: number;
  enabled: boolean;
}

export interface RssGeneratedBook {
  id: number;
  feed_id: number;
  title: string;
  filename: string;
  file_size: number | null;
  article_count: number;
  generation_date: string;
  calibre_book_id: number | null;
}

export const rssBooksApi = {
  getFeeds: async (): Promise<RssFeed[]> => {
    const response = await api.get('/rss/feeds');
    return response.data;
  },

  getBooks: async (feedId?: number, limit = 50): Promise<RssGeneratedBook[]> => {
    const params: { feed_id?: number; limit: number } = { limit };
    if (feedId) params.feed_id = feedId;
    const response = await api.get('/rss/books', { params });
    return response.data;
  },

  getDownloadUrl: (bookId: number): string => {
    return `${API_BASE_URL}/rss/books/${bookId}/download`;
  },

  generateFeed: async (feedId: number): Promise<{ success: boolean; files_generated: number; files: string[] }> => {
    const response = await api.post(`/rss/generate/${feedId}`);
    return response.data;
  },
};

// Favorites API
export interface Favorite {
  id: number;
  book_id: number;
  created_at: string;
}

export const favoritesApi = {
  getFavorites: async (): Promise<Favorite[]> => {
    const response = await api.get('/user/favorites');
    return response.data;
  },

  getFavoritesWithBooks: async (): Promise<Book[]> => {
    const response = await api.get('/user/favorites/books');
    return response.data;
  },

  addFavorite: async (bookId: number): Promise<Favorite> => {
    const response = await api.post(`/user/favorites/${bookId}`);
    return response.data;
  },

  removeFavorite: async (bookId: number): Promise<void> => {
    await api.delete(`/user/favorites/${bookId}`);
  },
};

export default api;
