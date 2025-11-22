import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { metadataApi } from '@/services/api';
import type { Publisher } from '@/types';
import { CompactList } from '@/components/CompactList';

export function PublishersPage() {
  const { t } = useTranslation();
  const [publishers, setPublishers] = useState<Publisher[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadPublishers();
  }, []);

  const loadPublishers = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await metadataApi.getPublishers();
      setPublishers(response);
    } catch (err) {
      setError(t('publishers.failedToLoad'));
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <CompactList
      items={publishers}
      getKey={(publisher) => publisher.id}
      getCount={(publisher) => publisher.count || 0}
      getName={(publisher) => publisher.name}
      getLink={(publisher) => `/publisher/new/${publisher.id}`}
      loading={loading}
      error={error}
      searchTerm={searchTerm}
      onSearchChange={setSearchTerm}
      title={t('publishers.title')}
      placeholder={t('publishers.placeholder')}
      itemLabel={t('publishers.label')}
    />
  );
}
