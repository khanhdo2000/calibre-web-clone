import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/contexts/AuthContext';
import { SearchBar } from './SearchBar';
import { BookOpen, Users, Building2, FolderTree, Menu, X, LogIn, LogOut, User } from 'lucide-react';

export function Header() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  const navItems = [
    { path: '/', label: t('navigation.books'), icon: BookOpen },
    { path: '/authors', label: t('navigation.authors'), icon: Users },
    { path: '/publishers', label: t('navigation.publishers'), icon: Building2 },
    { path: '/categories', label: t('navigation.categories'), icon: FolderTree },
  ];

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/' || location.pathname.startsWith('/page/');
    }
    return location.pathname.startsWith(path);
  };

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
      <div className="px-4 py-3">
        <div className="flex items-center gap-4">
          {/* Mobile menu button */}
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="md:hidden p-2 rounded-md text-gray-600 hover:bg-gray-100"
            aria-label="Toggle menu"
          >
            {menuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>

          {/* Logo - visible on mobile */}
          <Link to="/" className="md:hidden flex items-center gap-2 text-lg font-bold text-gray-800">
            <BookOpen className="w-6 h-6 text-blue-600" />
            <span>{t('common.calibre')}</span>
          </Link>

          {/* Search bar */}
          <div className="flex-1">
            <SearchBar />
          </div>

          {/* Auth buttons */}
          <div className="flex items-center gap-2">
            {user ? (
              <>
                <div className="hidden md:flex items-center gap-2 px-3 py-1.5 text-sm text-gray-700">
                  <User className="w-4 h-4" />
                  <span className="max-w-[150px] truncate">{user.full_name || user.email.split('@')[0]}</span>
                </div>
                <button
                  onClick={() => {
                    logout();
                    navigate('/');
                  }}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                  title={t('auth.logout')}
                >
                  <LogOut className="w-4 h-4" />
                  <span className="hidden md:inline">{t('auth.logout')}</span>
                </button>
              </>
            ) : (
              <Link
                to="/login"
                className="flex items-center gap-2 px-3 py-1.5 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
              >
                <LogIn className="w-4 h-4" />
                <span className="hidden md:inline">{t('auth.login.button')}</span>
              </Link>
            )}
          </div>
        </div>

        {/* Mobile collapsible menu */}
        {menuOpen && (
          <nav className="md:hidden mt-4 pb-4 border-t border-gray-200 pt-4">
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
                    onClick={() => setMenuOpen(false)}
                    className={`flex items-center gap-3 px-3 py-2 rounded-md transition-colors ${
                      active
                        ? 'bg-blue-50 text-blue-700 font-medium'
                        : 'text-gray-700 hover:bg-gray-100'
                    }`}
                  >
                    <Icon className={`w-5 h-5 ${active ? 'text-blue-600' : 'text-gray-500'}`} />
                    <span className="text-sm">{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </nav>
        )}
      </div>
    </header>
  );
}
