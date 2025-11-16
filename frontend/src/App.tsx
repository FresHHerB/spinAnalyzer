import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import VillainProfile from './pages/VillainProfile';
import Search from './pages/Search';
import FileUpload from './components/FileUpload';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/villain/:villainName" element={<VillainProfile />} />
          <Route path="/search" element={<Search />} />
          <Route path="/upload" element={<FileUpload />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
