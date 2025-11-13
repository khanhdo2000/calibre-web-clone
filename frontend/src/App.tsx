import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { HomePage } from './pages/HomePage';
import { SearchPage } from './pages/SearchPage';
import { BookDetailPage } from './pages/BookDetailPage';
import { ReaderPage } from './pages/ReaderPage';
import { AuthorsPage } from './pages/AuthorsPage';
import { PublishersPage } from './pages/PublishersPage';
import { CategoriesPage } from './pages/CategoriesPage';
import { DiscoverPage } from './pages/DiscoverPage';
import { PairPage } from './pages/PairPage';
import { SelectBooksPage } from './pages/SelectBooksPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/read/:id" element={<ReaderPage />} />
        <Route path="/pair" element={<PairPage />} />
        <Route path="/select-books" element={<SelectBooksPage />} />
        <Route
          path="/*"
          element={
            <div className="min-h-screen bg-gray-50 flex">
              <Sidebar />
              <div className="flex-1 flex flex-col">
                <Header />
                <main className="flex-1 p-4">
                  <Routes>
                    <Route path="/" element={<HomePage />} />
                    <Route path="/page/:page" element={<HomePage />} />
                    <Route path="/category/:sort_param/:id" element={<HomePage />} />
                    <Route path="/category/:sort_param/:id/page/:page" element={<HomePage />} />
                    <Route path="/author/:sort_param/:id" element={<HomePage />} />
                    <Route path="/author/:sort_param/:id/page/:page" element={<HomePage />} />
                    <Route path="/publisher/:sort_param/:id" element={<HomePage />} />
                    <Route path="/publisher/:sort_param/:id/page/:page" element={<HomePage />} />
                    <Route path="/series/:sort_param/:id" element={<HomePage />} />
                    <Route path="/series/:sort_param/:id/page/:page" element={<HomePage />} />
                    <Route path="/search/:sort_param" element={<SearchPage />} />
                  <Route path="/search/:sort_param/page/:page" element={<SearchPage />} />
                    <Route path="/book/:id" element={<BookDetailPage />} />
                    <Route path="/discover" element={<DiscoverPage />} />
                    <Route path="/authors" element={<AuthorsPage />} />
                    <Route path="/publishers" element={<PublishersPage />} />
                    <Route path="/categories" element={<CategoriesPage />} />
                  </Routes>
                </main>
              </div>
            </div>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
