import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppShell from './components/layout/AppShell';
import SubmitPage from './pages/SubmitPage';
import DashboardPage from './pages/DashboardPage';
import BuilderPage from './pages/BuilderPage';
import StyleRulesPage from './pages/StyleRulesPage';
import EditPage from './pages/EditPage';
import SettingsPage from './pages/SettingsPage';
import RecurringMessagesPage from './pages/RecurringMessagesPage';
import LandingPage from './pages/LandingPage';
import RetiredToolPage from './pages/RetiredToolPage';
import { RETIRED_TOOL_PATHS } from './utils/retiredTools';
import DataGovernancePage from './pages/DataGovernancePage';
import FeedbackPage from './pages/FeedbackPage';
import SsoCallbackPage, { SSO_CALLBACK_PATH } from './pages/SsoCallbackPage';
import LoginPage from './pages/LoginPage';
import { LOGIN_PATH } from './auth/loginUrl';
import RequireRole from './auth/RequireRole';
import EnvironmentBanner from './components/layout/EnvironmentBanner';

export default function App() {
  return (
    <BrowserRouter>
      <EnvironmentBanner />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path={LOGIN_PATH} element={<LoginPage />} />
        <Route path={SSO_CALLBACK_PATH} element={<SsoCallbackPage />} />
        {/* SLC and Event Services tools are hidden pending a move to their own
            app; old bookmarks land on a notice instead of a blank page. */}
        {RETIRED_TOOL_PATHS.map((path) => (
          <Route key={path} path={path} element={<RetiredToolPage />} />
        ))}
        <Route element={<RequireRole />}>
          <Route element={<AppShell />}>
            <Route path="/home" element={<Navigate to="/dashboard" replace />} />
            <Route path="/submit" element={<SubmitPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/edit/:id" element={<EditPage />} />
            <Route path="/builder" element={<BuilderPage />} />
            <Route path="/recurring-messages" element={<RecurringMessagesPage />} />
            <Route path="/style-rules" element={<StyleRulesPage />} />
            <Route path="/feedback" element={<FeedbackPage />} />
            <Route path="/data-governance" element={<DataGovernancePage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
