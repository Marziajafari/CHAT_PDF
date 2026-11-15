import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Chat from "./pages/Chat";
import Dashboard from "./pages/Dashboard";
import Documents from "./pages/Documents";
import Flashcards from "./pages/Flashcards";
import History from "./pages/History";
import Quiz from "./pages/Quiz";
import Settings from "./pages/Settings";
import Summaries from "./pages/Summaries";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="documents" element={<Documents />} />
        <Route path="chat" element={<Chat />} />
        <Route path="summaries" element={<Summaries />} />
        <Route path="quiz" element={<Quiz />} />
        <Route path="flashcards" element={<Flashcards />} />
        <Route path="history" element={<History />} />
        <Route path="settings" element={<Settings />} />
        <Route path="*" element={<Dashboard />} />
      </Route>
    </Routes>
  );
}
