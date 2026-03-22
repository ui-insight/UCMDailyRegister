import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppShell from './components/layout/AppShell';
import SubmitPage from './pages/SubmitPage';
import DashboardPage from './pages/DashboardPage';
import BuilderPage from './pages/BuilderPage';
import StyleRulesPage from './pages/StyleRulesPage';
import EditPage from './pages/EditPage';
import SettingsPage from './pages/SettingsPage';
import RecurringMessagesPage from './pages/RecurringMessagesPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/submit" element={<SubmitPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/edit/:id" element={<EditPage />} />
          <Route path="/builder" element={<BuilderPage />} />
          <Route path="/recurring-messages" element={<RecurringMessagesPage />} />
          <Route path="/style-rules" element={<StyleRulesPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
