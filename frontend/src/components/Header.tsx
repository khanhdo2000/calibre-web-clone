import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/contexts/AuthContext';
import { SearchBar } from './SearchBar';
import { BookOpen, Users, Building2, FolderTree, Menu, X, LogIn, LogOut, User, Home, Sparkles, Folders, Newspaper } from 'lucide-react';

export function Header() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  const navItems = [
    { path: '/', label: t('navigation.home'), icon: Home },
    { path: '/books', label: t('navigation.books'), icon: BookOpen },
    { path: '/discover', label: t('navigation.discover'), icon: Sparkles },
    { path: '/authors', label: t('navigation.authors'), icon: Users },
    { path: '/publishers', label: t('navigation.publishers'), icon: Building2 },
    { path: '/tags', label: t('navigation.tags'), icon: FolderTree },
    { path: '/categories', label: t('navigation.categories'), icon: Folders },
    { path: '/news', label: 'Tin tức', icon: Newspaper },
  ];

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    if (path === '/books') {
      return location.pathname.startsWith('/books') || location.pathname.startsWith('/page/') || location.pathname.startsWith('/book/');
    }
    if (path === '/discover') {
      return location.pathname === '/discover';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <>
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
      </div>
      </header>

      {/* Mobile full-screen menu overlay */}
      {menuOpen && (
        <>
          {/* Backdrop */}
          <div
            className="md:hidden fixed inset-0 bg-black bg-opacity-50 z-40"
            onClick={() => setMenuOpen(false)}
          />

          {/* Menu content */}
          <div className="md:hidden fixed inset-0 top-[60px] bg-white z-50 overflow-y-auto animate-in slide-in-from-top duration-200">
            <nav className="px-4 py-4">
              {/* User info section (mobile only) */}
              {user && (
                <div className="mb-6 pb-4 border-b border-gray-200">
                  <div className="flex items-center gap-3 px-3 py-2">
                    <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                      <User className="w-5 h-5 text-blue-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-gray-800 truncate">
                        {user.full_name || user.email.split('@')[0]}
                      </p>
                      <p className="text-xs text-gray-500 truncate">{user.email}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Navigation items */}
              <div className="space-y-1">
                <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider px-3 py-2 mb-2">
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
                      className={`flex items-center gap-4 px-4 py-3 rounded-lg transition-colors ${
                        active
                          ? 'bg-blue-50 text-blue-700 font-medium'
                          : 'text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      <Icon className={`w-5 h-5 flex-shrink-0 ${active ? 'text-blue-600' : 'text-gray-500'}`} />
                      <span className="text-base">{item.label}</span>
                    </Link>
                  );
                })}
              </div>

              {/* Auth section at bottom */}
              {!user && (
                <div className="mt-6 pt-4 border-t border-gray-200">
                  <Link
                    to="/login"
                    onClick={() => setMenuOpen(false)}
                    className="flex items-center justify-center gap-2 w-full px-4 py-3 text-base font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
                  >
                    <LogIn className="w-5 h-5" />
                    <span>{t('auth.login.button')}</span>
                  </Link>
                </div>
              )}
            </nav>
          </div>
        </>
      )}
    </>
  );
}
