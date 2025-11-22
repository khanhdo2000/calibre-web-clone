import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { metadataApi } from '@/services/api';
import type { Category } from '@/types';
import { CompactList } from '@/components/CompactList';

export function TagsPage() {
  const { t } = useTranslation();
  const [tags, setTags] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadTags();
  }, []);

  const loadTags = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await metadataApi.getTags();
      setTags(response);
    } catch (err) {
      setError(t('tags.failedToLoad'));
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <CompactList
      items={tags}
      getKey={(tag) => tag.id}
      getCount={(tag) => tag.count}
      getName={(tag) => tag.name}
      getLink={(tag) => tag.id === -1 ? '/category/new/-1' : `/category/new/${tag.id}`}
      loading={loading}
      error={error}
      searchTerm={searchTerm}
      onSearchChange={setSearchTerm}
      title={t('tags.title')}
      placeholder={t('tags.placeholder')}
      itemLabel={t('tags.label')}
    />
  );
}

