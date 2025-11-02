import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { metadataApi } from '@/services/api';
import type { Author } from '@/types';
import { CompactList } from '@/components/CompactList';

export function AuthorsPage() {
  const { t } = useTranslation();
  const [authors, setAuthors] = useState<Author[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadAuthors();
  }, []);

  const loadAuthors = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await metadataApi.getAuthors();
      setAuthors(response);
    } catch (err) {
      setError(t('authors.failedToLoad'));
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <CompactList
      items={authors}
      getKey={(author) => author.id}
      getCount={(author) => author.count || 0}
      getName={(author) => author.name}
      getLink={(author) => `/author/stored/${author.id}`}
      loading={loading}
      error={error}
      searchTerm={searchTerm}
      onSearchChange={setSearchTerm}
      title={t('authors.title')}
      placeholder={t('authors.placeholder')}
      itemLabel={t('authors.label')}
    />
  );
}
