import { ReactNode, useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

interface CompactListProps<T> {
  items: T[];
  getKey: (item: T) => string | number;
  getCount: (item: T) => number;
  getName: (item: T) => string;
  getLink: (item: T) => string;
  loading: boolean;
  error: string | null;
  searchTerm: string;
  onSearchChange: (term: string) => void;
  title: string;
  placeholder: string;
  itemLabel: string;
  renderItem?: (item: T) => ReactNode;
}

export function CompactList<T>({
  items,
  getKey,
  getCount,
  getName,
  getLink,
  loading,
  error,
  searchTerm,
  onSearchChange,
  title,
  placeholder,
  itemLabel,
  renderItem,
}: CompactListProps<T>) {
  const { t } = useTranslation();
  const [selectedChar, setSelectedChar] = useState<string | null>(null);

  // Normalize Vietnamese text by removing diacritics
  const normalizeVietnamese = (str: string): string => {
    return str
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '') // Remove diacritics
      .replace(/đ/g, 'd')
      .replace(/Đ/g, 'D')
      .toLowerCase();
  };

  // Generate alphabet filter list from items
  const alphabetChars = useMemo(() => {
    const chars = new Set<string>();
    items.forEach((item) => {
      const name = getName(item);
      if (name && name.length > 0) {
        const firstChar = name[0].toUpperCase();
        if (/[A-Z0-9]/.test(firstChar)) {
          chars.add(firstChar);
        }
      }
    });
    return Array.from(chars).sort();
  }, [items, getName]);

  // Filter items by search term and alphabet (supports Vietnamese without diacritics)
  const filteredItems = useMemo(() => {
    let result = items.filter((item) => {
      const name = getName(item);
      const normalizedName = normalizeVietnamese(name);
      const normalizedSearch = normalizeVietnamese(searchTerm);
      return normalizedName.includes(normalizedSearch);
    });

    if (selectedChar) {
      result = result.filter((item) => {
        const name = getName(item);
        return name && name.length > 0 && name[0].toUpperCase() === selectedChar;
      });
    }

    return result;
  }, [items, searchTerm, selectedChar, getName]);

  const handleCharClick = (char: string | null) => {
    setSelectedChar(char);
  };

  // Split items into two columns if there are more than 20 items
  const useTwoColumns = filteredItems.length > 20;
  const midpoint = Math.ceil(filteredItems.length / 2);
  const firstColumn = useTwoColumns ? filteredItems.slice(0, midpoint) : filteredItems;
  const secondColumn = useTwoColumns ? filteredItems.slice(midpoint) : [];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">{t('common.loading')}</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center text-red-600">
          <p className="text-xl font-semibold mb-2">{t('common.error')}</p>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  const renderItemRow = (item: T) => {
    if (renderItem) {
      return renderItem(item);
    }

    return (
      <div key={getKey(item)} className="flex items-center text-sm hover:bg-gray-50">
        <div className="w-10 px-2 text-right">
          <span className="inline-block px-1.5 py-0.5 text-xs font-semibold text-gray-600 bg-gray-100 rounded">
            {getCount(item)}
          </span>
        </div>
        <div className="flex-1 py-1.5">
          <Link
            to={getLink(item)}
            className="text-gray-800 hover:text-blue-600 hover:underline"
          >
            {getName(item)}
          </Link>
        </div>
      </div>
    );
  };

  return (
    <div>
      <div className="mb-4">
        <h1 className="text-xl font-semibold text-gray-800 mb-3">{title}</h1>
        
        {/* Alphabet Filter */}
        {alphabetChars.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-1 items-center">
            <button
              onClick={() => handleCharClick(null)}
              className={`px-2 py-1 text-xs font-medium rounded transition-colors ${
                selectedChar === null
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {t('common.all')}
            </button>
            {alphabetChars.map((char) => (
              <button
                key={char}
                onClick={() => handleCharClick(char)}
                className={`px-2 py-1 text-xs font-medium rounded transition-colors ${
                  selectedChar === char
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {char}
              </button>
            ))}
          </div>
        )}

        <input
          type="text"
          placeholder={placeholder}
          value={searchTerm}
          onChange={(e) => {
            onSearchChange(e.target.value);
            // Reset alphabet filter when searching
            if (e.target.value) {
              setSelectedChar(null);
            }
          }}
          className="w-full max-w-md px-3 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <p className="text-xs text-gray-500 mt-1.5">
          {filteredItems.length} {filteredItems.length === 1 ? itemLabel : `${itemLabel}s`}
        </p>
      </div>

      <div className={`grid ${useTwoColumns ? 'grid-cols-1 md:grid-cols-2 gap-x-4' : ''}`}>
        <div className="bg-white rounded border border-gray-200 divide-y divide-gray-100">
          {firstColumn.map(renderItemRow)}
        </div>
        {useTwoColumns && (
          <div className="bg-white rounded border border-gray-200 divide-y divide-gray-100">
            {secondColumn.map(renderItemRow)}
          </div>
        )}
      </div>

      {filteredItems.length === 0 && (searchTerm || selectedChar) && (
        <div className="text-center text-gray-600 mt-6 text-sm">
          <p>
            {t('common.noItemsFound', { itemLabel })}
            {searchTerm && ` ${t('common.matching', { term: searchTerm })}`}
            {selectedChar && ` ${t('common.startingWith', { char: selectedChar })}`}
          </p>
        </div>
      )}
    </div>
  );
}

