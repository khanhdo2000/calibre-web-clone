import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { categoryGroupsApi, metadataApi } from '@/services/api';
import type { CategoryGroup, Category, CategoryGroupCreate, CategoryGroupUpdate } from '@/types';
import { Plus, Edit, Trash2, Save, X, FolderTree, GripVertical, Search } from 'lucide-react';

export function CategoriesManagementPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [categories, setCategories] = useState<CategoryGroup[]>([]);
  const [allTags, setAllTags] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [isSavingOrder, setIsSavingOrder] = useState(false);
  const [tagFilter, setTagFilter] = useState('');

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    tag_ids: [] as number[],
  });

  // Redirect if not admin
  useEffect(() => {
    if (user && !user.is_admin) {
      navigate('/');
    }
  }, [user, navigate]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [categoriesData, tagsData] = await Promise.all([
        categoryGroupsApi.getAll(),
        metadataApi.getTags(),
      ]);
      setCategories(categoriesData.categories);
      setAllTags(tagsData);
    } catch (err: any) {
      setError(err.response?.data?.detail || t('categories.failedToLoad'));
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setIsCreating(true);
    setEditingId(null);
    setFormData({ name: '', description: '', tag_ids: [] });
  };

  const handleEdit = (category: CategoryGroup) => {
    setEditingId(category.id);
    setIsCreating(false);
    setFormData({
      name: category.name,
      description: category.description || '',
      tag_ids: category.tags.map(t => t.id),
    });
  };

  const handleCancel = () => {
    setIsCreating(false);
    setEditingId(null);
    setFormData({ name: '', description: '', tag_ids: [] });
    setTagFilter('');
  };

  const handleSave = async () => {
    if (!formData.name.trim()) {
      setError(t('categories.nameRequired'));
      return;
    }

    try {
      if (isCreating) {
        const data: CategoryGroupCreate = {
          name: formData.name,
          description: formData.description || undefined,
          tag_ids: formData.tag_ids,
        };
        await categoryGroupsApi.create(data);
      } else if (editingId) {
        const data: CategoryGroupUpdate = {
          name: formData.name,
          description: formData.description || undefined,
          tag_ids: formData.tag_ids,
        };
        await categoryGroupsApi.update(editingId, data);
      }
      await loadData();
      handleCancel();
    } catch (err: any) {
      setError(err.response?.data?.detail || t('categories.failedToSave'));
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm(t('categories.confirmDelete'))) {
      return;
    }

    try {
      await categoryGroupsApi.delete(id);
      await loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail || t('categories.failedToDelete'));
    }
  };

  const toggleTag = (tagId: number) => {
    setFormData(prev => ({
      ...prev,
      tag_ids: prev.tag_ids.includes(tagId)
        ? prev.tag_ids.filter(id => id !== tagId)
        : [...prev.tag_ids, tagId],
    }));
  };

  // Normalize Vietnamese text by removing diacritics
  const normalizeVietnamese = (str: string): string => {
    return str
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '') // Remove diacritics
      .replace(/đ/g, 'd')
      .replace(/Đ/g, 'D')
      .toLowerCase();
  };

  // Filter tags based on search query (supports Vietnamese without diacritics)
  const filteredTags = allTags.filter(tag => {
    if (tag.id === -1) return false;

    const normalizedTagName = normalizeVietnamese(tag.name);
    const normalizedFilter = normalizeVietnamese(tagFilter);

    return normalizedTagName.includes(normalizedFilter);
  });

  const handleDragStart = (index: number) => {
    setDraggedIndex(index);
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === index) return;

    const newCategories = [...categories];
    const draggedItem = newCategories[draggedIndex];
    newCategories.splice(draggedIndex, 1);
    newCategories.splice(index, 0, draggedItem);

    setCategories(newCategories);
    setDraggedIndex(index);
  };

  const handleDragEnd = async () => {
    if (draggedIndex === null) return;

    setIsSavingOrder(true);
    try {
      // Update display_order based on new positions
      const reorderData = categories.map((cat, index) => ({
        id: cat.id,
        display_order: index * 10, // Use increments of 10 for easier future reordering
      }));

      await categoryGroupsApi.reorder(reorderData);
      await loadData(); // Reload to get fresh data
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save category order');
      await loadData(); // Reload on error to reset order
    } finally {
      setDraggedIndex(null);
      setIsSavingOrder(false);
    }
  };

  if (!user?.is_admin) {
    return null;
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center">{t('common.loading')}</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <FolderTree className="w-8 h-8 text-blue-600" />
          <h1 className="text-3xl font-bold text-gray-800">{t('categories.management.title')}</h1>
        </div>
        {!isCreating && !editingId && (
          <button
            onClick={handleCreate}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-5 h-5" />
            {t('categories.management.createNew')}
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {/* Create/Edit Form */}
      {(isCreating || editingId) && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6 border border-gray-200">
          <h2 className="text-xl font-semibold mb-4">
            {isCreating ? t('categories.management.createNew') : t('categories.management.edit')}
          </h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('categories.management.name')} *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder={t('categories.management.namePlaceholder')}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('categories.management.description')}
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                rows={3}
                placeholder={t('categories.management.descriptionPlaceholder')}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('categories.management.selectTags')}
              </label>

              {/* Search/Filter Input */}
              <div className="relative mb-3">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Search className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  type="text"
                  value={tagFilter}
                  onChange={(e) => setTagFilter(e.target.value)}
                  className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder={t('i18n.language') === 'vi' ? 'Tìm kiếm thẻ...' : 'Search tags...'}
                />
                {tagFilter && (
                  <button
                    onClick={() => setTagFilter('')}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                  >
                    <X className="h-5 w-5" />
                  </button>
                )}
              </div>

              <div className="border border-gray-300 rounded-lg p-4 max-h-64 overflow-y-auto">
                {allTags.length === 0 ? (
                  <p className="text-gray-500 text-sm">{t('categories.management.noTags')}</p>
                ) : filteredTags.length === 0 ? (
                  <p className="text-gray-500 text-sm text-center py-4">
                    {t('i18n.language') === 'vi' ? 'Không tìm thấy thẻ nào' : 'No tags found'}
                  </p>
                ) : (
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                    {filteredTags.map((tag) => (
                      <label key={tag.id} className="flex items-center space-x-2 cursor-pointer hover:bg-gray-50 p-2 rounded">
                        <input
                          type="checkbox"
                          checked={formData.tag_ids.includes(tag.id)}
                          onChange={() => toggleTag(tag.id)}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <span className="text-sm text-gray-700">{tag.name}</span>
                        {tag.count !== undefined && (
                          <span className="text-xs text-gray-500">({tag.count})</span>
                        )}
                      </label>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex items-center justify-between mt-2">
                <p className="text-sm text-gray-500">
                  {t('categories.management.selectedCount', { count: formData.tag_ids.length })}
                </p>
                {tagFilter && (
                  <p className="text-xs text-gray-500">
                    {t('i18n.language') === 'vi'
                      ? `Hiển thị ${filteredTags.length} / ${allTags.filter(tag => tag.id !== -1).length} thẻ`
                      : `Showing ${filteredTags.length} / ${allTags.filter(tag => tag.id !== -1).length} tags`}
                  </p>
                )}
              </div>
            </div>

            <div className="flex gap-3 pt-4">
              <button
                onClick={handleSave}
                className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors"
              >
                <Save className="w-4 h-4" />
                {t('common.save')}
              </button>
              <button
                onClick={handleCancel}
                className="flex items-center gap-2 bg-gray-500 text-white px-4 py-2 rounded-lg hover:bg-gray-600 transition-colors"
              >
                <X className="w-4 h-4" />
                {t('common.cancel')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Categories List */}
      {isSavingOrder && (
        <div className="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded-lg mb-4">
          Saving category order...
        </div>
      )}

      <div className="space-y-4">
        {categories.length === 0 ? (
          <div className="bg-white rounded-lg shadow-md p-8 text-center">
            <FolderTree className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">{t('categories.management.empty')}</p>
          </div>
        ) : (
          <>
            <div className="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded-lg mb-4">
              <p className="text-sm">💡 Drag and drop categories to reorder them on the home page</p>
            </div>
            {categories.map((category, index) => (
              <div
                key={category.id}
                draggable={!editingId && !isCreating}
                onDragStart={() => handleDragStart(index)}
                onDragOver={(e) => handleDragOver(e, index)}
                onDragEnd={handleDragEnd}
                className={`bg-white rounded-lg shadow-md p-6 border border-gray-200 hover:shadow-lg transition-shadow ${
                  draggedIndex === index ? 'opacity-50' : ''
                } ${!editingId && !isCreating ? 'cursor-move' : ''}`}
              >
                <div className="flex items-start gap-3">
                  {!editingId && !isCreating && (
                    <div className="pt-1 text-gray-400 cursor-move">
                      <GripVertical className="w-5 h-5" />
                    </div>
                  )}
                  <div className="flex-1">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex-1">
                        <h3 className="text-xl font-semibold text-gray-800 mb-2">{category.name}</h3>
                        {category.description && (
                          <p className="text-gray-600 text-sm mb-3">{category.description}</p>
                        )}
                        {category.book_count !== undefined && (
                          <p className="text-sm text-gray-500">
                            {t('categories.management.bookCount', { count: category.book_count })}
                          </p>
                        )}
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleEdit(category)}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          title={t('common.edit')}
                        >
                          <Edit className="w-5 h-5" />
                        </button>
                        <button
                          onClick={() => handleDelete(category.id)}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          title={t('common.delete')}
                        >
                          <Trash2 className="w-5 h-5" />
                        </button>
                      </div>
                    </div>

                    {category.tags.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {category.tags.map((tag) => (
                          <span
                            key={tag.id}
                            className="bg-blue-50 text-blue-700 px-3 py-1 rounded-full text-sm"
                          >
                            {tag.name}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
