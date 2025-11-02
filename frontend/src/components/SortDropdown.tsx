import { useNavigate, useLocation } from 'react-router-dom';
import { ArrowUpDown, BookOpen, Calendar, User, ListOrdered } from 'lucide-react';

interface SortOption {
  value: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

interface SortDropdownProps {
  currentSort?: string;
  showSeriesSort?: boolean;
}

export function SortDropdown({ currentSort = 'new', showSeriesSort = false }: SortDropdownProps) {
  const navigate = useNavigate();
  const location = useLocation();

  const sortOptions: SortOption[] = [
    { value: 'new', label: 'Newest First', icon: Calendar },
    { value: 'old', label: 'Oldest First', icon: Calendar },
    { value: 'abc', label: 'Title A-Z', icon: BookOpen },
    { value: 'zyx', label: 'Title Z-A', icon: BookOpen },
    { value: 'authaz', label: 'Author A-Z', icon: User },
    { value: 'authza', label: 'Author Z-A', icon: User },
    { value: 'pubnew', label: 'Publication Date (New)', icon: Calendar },
    { value: 'pubold', label: 'Publication Date (Old)', icon: Calendar },
  ];

  if (showSeriesSort) {
    sortOptions.push(
      { value: 'seriesasc', label: 'Series Index (Asc)', icon: ListOrdered },
      { value: 'seriesdesc', label: 'Series Index (Desc)', icon: ListOrdered }
    );
  }

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

  return (
    <div className="relative inline-block">
      <select
        value={currentSort}
        onChange={(e) => handleSortChange(e.target.value)}
        className="appearance-none bg-white border border-gray-300 rounded-lg px-4 py-2 pr-10 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 cursor-pointer"
      >
        {sortOptions.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
        <ArrowUpDown className="h-4 w-4 text-gray-500" />
      </div>
    </div>
  );
}

