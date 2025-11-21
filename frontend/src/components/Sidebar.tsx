import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { BookOpen, Users, Building2, FolderTree, Sparkles, Folders, Home } from 'lucide-react';

export function Sidebar() {
  const { t } = useTranslation();
  const location = useLocation();

  const navItems = [
    { path: '/', label: t('navigation.home'), icon: Home },
    { path: '/books', label: t('navigation.books'), icon: BookOpen },
    { path: '/discover', label: t('navigation.discover'), icon: Sparkles },
    { path: '/authors', label: t('navigation.authors'), icon: Users },
    { path: '/publishers', label: t('navigation.publishers'), icon: Building2 },
    { path: '/tags', label: t('navigation.tags'), icon: FolderTree },
    { path: '/categories', label: t('navigation.categories'), icon: Folders },
  ];

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    if (path === '/books') {
      return location.pathname.startsWith('/books') || location.pathname.startsWith('/page/');
    }
    if (path === '/discover') {
      return location.pathname === '/discover';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <nav className="hidden md:block w-48 bg-white border-r border-gray-200 min-h-screen sticky top-0 h-screen overflow-y-auto">
      <div className="p-4">
        <Link to="/" className="flex items-center gap-2 text-lg font-bold text-gray-800 mb-6">
          <BookOpen className="w-6 h-6 text-blue-600" />
          <span>{t('common.calibre')}</span>
        </Link>

        <div className="space-y-1">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider px-3 py-2">
            {t('common.browse')}
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3 py-2 rounded-md transition-colors ${
                  active
                    ? 'bg-blue-50 text-blue-700 font-medium'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <Icon className={`w-4 h-4 ${active ? 'text-blue-600' : 'text-gray-500'}`} />
                <span className="text-sm">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}

