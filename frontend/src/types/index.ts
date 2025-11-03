export interface Author {
  id: number;
  name: string;
  count?: number;
}

export interface Tag {
  id: number;
  name: string;
  count?: number;
}

export interface Series {
  id: number;
  name: string;
  index?: number;
  count?: number;
}

export interface Publisher {
  id: number;
  name: string;
  count?: number;
}

export interface Category {
  id: number;
  name: string;
  count: number;
}

export interface Book {
  id: number;
  title: string;
  authors: Author[];
  tags: Tag[];
  series?: Series;
  publisher?: Publisher;
  pubdate?: string;
  timestamp?: string;
  last_modified?: string;
  path: string;
  has_cover: boolean;
  cover_url?: string | null; // S3 URL if cover is uploaded to S3 (full-size)
  cover_thumb_url?: string | null; // S3 URL for thumbnail (optimized for list view)
  uuid?: string;
  isbn?: string;
  lccn?: string;
  rating?: number;
  file_formats: string[];
  file_size?: number;
  comments?: string;
}

export interface BookDetail extends Book {
  languages: string[];
  identifiers: Record<string, string>;
}

export interface BookListResponse {
  total: number;
  page: number;
  per_page: number;
  books: Book[];
}

export interface SearchResult {
  books: Book[];
  total: number;
  query: string;
}

export interface FilterOptions {
  page?: number;
  per_page?: number;
  sort_by?: 'id' | 'title' | 'timestamp' | 'pubdate' | 'last_modified';
  order?: 'asc' | 'desc';
  sort_param?: 'new' | 'old' | 'abc' | 'zyx' | 'authaz' | 'authza' | 'pubnew' | 'pubold' | 'seriesasc' | 'seriesdesc';
  author_id?: number;
  series_id?: number;
  publisher_id?: number;
  tag_id?: number;
  search_query?: string;
}
