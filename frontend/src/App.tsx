import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { FavoritesProvider } from './contexts/FavoritesContext';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { HomePage } from './pages/HomePage';
import { BooksPage } from './pages/BooksPage';
import { SearchPage } from './pages/SearchPage';
import { BookDetailPage } from './pages/BookDetailPage';
import { ReaderPage } from './pages/ReaderPage';
import { AuthorsPage } from './pages/AuthorsPage';
import { PublishersPage } from './pages/PublishersPage';
import { TagsPage } from './pages/TagsPage';
import { CategoriesPage } from './pages/CategoriesPage';
import { CategoryViewPage } from './pages/CategoryViewPage';
import { CategoriesManagementPage } from './pages/CategoriesManagementPage';
import { DiscoverPage } from './pages/DiscoverPage';
import { PairPage } from './pages/PairPage';
import { SelectBooksPage } from './pages/SelectBooksPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { VerifyEmailPage } from './pages/VerifyEmailPage';
import { RssBooksPage } from './pages/RssBooksPage';
import { FavoritesPage } from './pages/FavoritesPage';

function MainLayout() {
  const location = useLocation();
  const isHomePage = location.pathname === '/';

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <main className={`flex-1 ${isHomePage ? 'md:p-4' : 'p-4'}`}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/books" element={<BooksPage />} />
            <Route path="/books/page/:page" element={<BooksPage />} />
            <Route path="/category/:sort_param/:id" element={<BooksPage />} />
            <Route path="/category/:sort_param/:id/page/:page" element={<BooksPage />} />
            <Route path="/author/:sort_param/:id" element={<BooksPage />} />
            <Route path="/author/:sort_param/:id/page/:page" element={<BooksPage />} />
            <Route path="/publisher/:sort_param/:id" element={<BooksPage />} />
            <Route path="/publisher/:sort_param/:id/page/:page" element={<BooksPage />} />
            <Route path="/series/:sort_param/:id" element={<BooksPage />} />
            <Route path="/series/:sort_param/:id/page/:page" element={<BooksPage />} />
            <Route path="/search/:sort_param" element={<SearchPage />} />
            <Route path="/search/:sort_param/page/:page" element={<SearchPage />} />
            <Route path="/book/:id" element={<BookDetailPage />} />
            <Route path="/discover" element={<DiscoverPage />} />
            <Route path="/authors" element={<AuthorsPage />} />
            <Route path="/publishers" element={<PublishersPage />} />
            <Route path="/tags" element={<TagsPage />} />
            <Route path="/categories" element={<CategoriesPage />} />
            <Route path="/categories/manage" element={<CategoriesManagementPage />} />
            <Route path="/categories/:id" element={<CategoryViewPage />} />
            <Route path="/news" element={<RssBooksPage />} />
            <Route path="/favorites" element={<FavoritesPage />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <FavoritesProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/verify-email" element={<VerifyEmailPage />} />
            <Route path="/read/:id" element={<ReaderPage />} />
            <Route path="/pair" element={<PairPage />} />
            <Route path="/select-books" element={<SelectBooksPage />} />
            <Route path="/*" element={<MainLayout />} />
          </Routes>
        </BrowserRouter>
      </FavoritesProvider>
    </AuthProvider>
  );
}

export default App;
