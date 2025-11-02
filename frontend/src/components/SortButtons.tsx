import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { BookOpen, Calendar, User, ArrowUp, ArrowDown, ListOrdered } from 'lucide-react';

interface SortButtonsProps {
  currentSort?: string;
  showSeriesSort?: boolean;
}

export function SortButtons({ currentSort = 'new', showSeriesSort = false }: SortButtonsProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();

  const handleSortChange = (sortValue: string) => {
    const pathParts = location.pathname.split('/');
    
    // Handle different URL patterns - preserve existing route structure
    if (pathParts[1] === 'category' || pathParts[1] === 'author' || 
        pathParts[1] === 'publisher' || pathParts[1] === 'series') {
      // Pattern: /category/:sort_param/:id or /category/:sort_param/:id/page/:page
      const dataType = pathParts[1];
      const id = pathParts[3];
      const page = pathParts[5] || '';
      
      if (page) {
        navigate(`/${dataType}/${sortValue}/${id}/page/${page}`);
      } else {
        navigate(`/${dataType}/${sortValue}/${id}`);
      }
    } else {
      // For root and page routes, use query params
      const params = new URLSearchParams(location.search);
      params.set('sort', sortValue);
      // Reset to page 1 when changing sort
      if (pathParts[1] === 'page') {
        navigate(`/?sort=${sortValue}`);
      } else {
        navigate(`${location.pathname}?${params.toString()}`);
      }
    }
    
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const buttonClass = (value: string) => {
    const baseClass = "px-3 py-2 text-sm font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2";
    const activeClass = "bg-blue-600 text-white shadow-md";
    const inactiveClass = "bg-gray-100 text-gray-700 hover:bg-gray-200";
    return `${baseClass} ${currentSort === value ? activeClass : inactiveClass}`;
  };

  return (
    <div className="flex flex-wrap gap-2 items-center">
      {/* Newest First */}
      <button
        onClick={() => handleSortChange('new')}
        className={buttonClass('new')}
        title={t('sort.newest')}
      >
        <div className="flex items-center gap-1">
          <BookOpen className="w-4 h-4" />
          <Calendar className="w-4 h-4" />
          <ArrowDown className="w-3 h-3" />
        </div>
      </button>

      {/* Oldest First */}
      <button
        onClick={() => handleSortChange('old')}
        className={buttonClass('old')}
        title={t('sort.oldest')}
      >
        <div className="flex items-center gap-1">
          <BookOpen className="w-4 h-4" />
          <Calendar className="w-4 h-4" />
          <ArrowUp className="w-3 h-3" />
        </div>
      </button>

      {/* Title A-Z */}
      <button
        onClick={() => handleSortChange('abc')}
        className={buttonClass('abc')}
        title={t('sort.titleAsc')}
      >
        <div className="flex items-center gap-1">
          <BookOpen className="w-4 h-4" />
          <ArrowDown className="w-3 h-3" />
        </div>
      </button>

      {/* Title Z-A */}
      <button
        onClick={() => handleSortChange('zyx')}
        className={buttonClass('zyx')}
        title={t('sort.titleDesc')}
      >
        <div className="flex items-center gap-1">
          <BookOpen className="w-4 h-4" />
          <ArrowUp className="w-3 h-3" />
        </div>
      </button>

      {/* Author A-Z */}
      <button
        onClick={() => handleSortChange('authaz')}
        className={buttonClass('authaz')}
        title={t('sort.authorAsc')}
      >
        <div className="flex items-center gap-1">
          <User className="w-4 h-4" />
          <ArrowDown className="w-3 h-3" />
        </div>
      </button>

      {/* Author Z-A */}
      <button
        onClick={() => handleSortChange('authza')}
        className={buttonClass('authza')}
        title={t('sort.authorDesc')}
      >
        <div className="flex items-center gap-1">
          <User className="w-4 h-4" />
          <ArrowUp className="w-3 h-3" />
        </div>
      </button>

      {/* Publication Date (New) */}
      <button
        onClick={() => handleSortChange('pubnew')}
        className={buttonClass('pubnew')}
        title={t('sort.pubNew')}
      >
        <div className="flex items-center gap-1">
          <Calendar className="w-4 h-4" />
          <ArrowDown className="w-3 h-3" />
        </div>
      </button>

      {/* Publication Date (Old) */}
      <button
        onClick={() => handleSortChange('pubold')}
        className={buttonClass('pubold')}
        title={t('sort.pubOld')}
      >
        <div className="flex items-center gap-1">
          <Calendar className="w-4 h-4" />
          <ArrowUp className="w-3 h-3" />
        </div>
      </button>

      {/* Series Index (only on series pages) */}
      {showSeriesSort && (
        <>
          <button
            onClick={() => handleSortChange('seriesasc')}
            className={buttonClass('seriesasc')}
            title={t('sort.seriesAsc')}
          >
            <div className="flex items-center gap-1">
              <ListOrdered className="w-4 h-4" />
              <ArrowDown className="w-3 h-3" />
            </div>
          </button>
          <button
            onClick={() => handleSortChange('seriesdesc')}
            className={buttonClass('seriesdesc')}
            title={t('sort.seriesDesc')}
          >
            <div className="flex items-center gap-1">
              <ListOrdered className="w-4 h-4" />
              <ArrowUp className="w-3 h-3" />
            </div>
          </button>
        </>
      )}
    </div>
  );
}

