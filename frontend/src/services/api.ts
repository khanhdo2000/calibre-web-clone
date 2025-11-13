import axios from 'axios';
import type {
  BookDetail,
  BookListResponse,
  SearchResult,
  Author,
  Series,
  Publisher,
  Category,
  FilterOptions,
} from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

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

  getCategories: async (): Promise<Category[]> => {
    const response = await api.get('/metadata/categories');
    return response.data;
  },
};

export default api;
