import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ReviewPage } from './pages/ReviewPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { DataPage } from './pages/DataPage';
import { TriagePage } from './pages/TriagePage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ReviewPage />} />
        <Route path="/triage" element={<TriagePage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/data" element={<DataPage />} />
      </Routes>
    </BrowserRouter>
  );
}
