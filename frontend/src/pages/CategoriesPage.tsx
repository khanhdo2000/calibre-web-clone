import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { categoryGroupsApi } from '@/services/api';
import type { CategoryGroup } from '@/types';
import { FolderTree, Settings, Search } from 'lucide-react';

export function CategoriesPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [categories, setCategories] = useState<CategoryGroup[]>([]);
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
      const data = await categoryGroupsApi.getAll();
      setCategories(data.categories);
    } catch (err: any) {
      setError(err.response?.data?.detail || t('categories.failedToLoad'));
    } finally {
      setLoading(false);
    }
  };

  const filteredCategories = categories.filter(category =>
    category.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    category.description?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center">{t('common.loading')}</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <FolderTree className="w-8 h-8 text-blue-600" />
          <h1 className="text-3xl font-bold text-gray-800">{t('categories.title')}</h1>
        </div>
        {user?.is_admin && (
          <Link
            to="/categories/manage"
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Settings className="w-5 h-5" />
            {t('categories.manage')}
          </Link>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {/* Search */}
      {categories.length > 0 && (
        <div className="mb-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder={t('categories.searchPlaceholder')}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
      )}

      {/* Categories Grid */}
      {filteredCategories.length === 0 ? (
        <div className="bg-gray-50 rounded-lg p-8 text-center">
          <FolderTree className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">
            {searchTerm ? t('categories.noResults') : t('categories.empty')}
          </p>
          {user?.is_admin && !searchTerm && (
            <Link
              to="/categories/manage"
              className="inline-block mt-4 text-blue-600 hover:underline"
            >
              {t('categories.createFirst')}
            </Link>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredCategories.map((category) => (
            <Link
              key={category.id}
              to={`/categories/${category.id}`}
              className="bg-white rounded-lg shadow-md p-6 border border-gray-200 hover:shadow-lg hover:border-blue-300 transition-all group"
            >
              <div className="flex items-start gap-4">
                <FolderTree className="w-8 h-8 text-blue-600 flex-shrink-0 group-hover:scale-110 transition-transform" />
                <div className="flex-1 min-w-0">
                  <h2 className="text-xl font-semibold text-gray-800 mb-2 group-hover:text-blue-600 transition-colors">
                    {category.name}
                  </h2>
                  {category.description && (
                    <p className="text-gray-600 text-sm mb-3 line-clamp-2">
                      {category.description}
                    </p>
                  )}
                  <div className="flex items-center justify-between">
                    {category.book_count !== undefined && (
                      <p className="text-sm text-gray-500">
                        {t('categories.bookCount', { count: category.book_count })}
                      </p>
                    )}
                    {category.tags.length > 0 && (
                      <p className="text-sm text-gray-500">
                        {t('categories.tagCount', { count: category.tags.length })}
                      </p>
                    )}
                  </div>
                  {category.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-3">
                      {category.tags.slice(0, 3).map((tag) => (
                        <span
                          key={tag.id}
                          className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full text-xs"
                        >
                          {tag.name}
                        </span>
                      ))}
                      {category.tags.length > 3 && (
                        <span className="text-blue-600 text-xs px-2 py-0.5">
                          +{category.tags.length - 3}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
