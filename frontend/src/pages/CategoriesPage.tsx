import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { metadataApi } from '@/services/api';
import type { Category } from '@/types';
import { CompactList } from '@/components/CompactList';

export function CategoriesPage() {
  const { t } = useTranslation();
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadCategories();
  }, []);

  const loadCategories = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await metadataApi.getCategories();
      setCategories(response);
    } catch (err) {
      setError(t('categories.failedToLoad'));
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <CompactList
      items={categories}
      getKey={(category) => category.id}
      getCount={(category) => category.count}
      getName={(category) => category.name}
      getLink={(category) => category.id === -1 ? '/category/stored/-1' : `/category/stored/${category.id}`}
      loading={loading}
      error={error}
      searchTerm={searchTerm}
      onSearchChange={setSearchTerm}
      title={t('categories.title')}
      placeholder={t('categories.placeholder')}
      itemLabel={t('categories.label')}
    />
  );
}

