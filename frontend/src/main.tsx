import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import "./index.css";
import { Layout } from "./components/Layout";
import { SettingsProvider } from "./lib/settings";
import Landing from "./pages/Landing";
import Workspace from "./pages/Workspace";
import Judge from "./pages/Judge";
import SpeakYourWay from "./pages/SpeakYourWay";
import { Evaluation, History, Privacy, Replay, SettingsPage, Sources, Status } from "./pages/InfoPages";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <SettingsProvider>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/app" element={<Workspace />} />
            <Route path="/judge" element={<Judge />} />
            <Route path="/speak-your-way" element={<SpeakYourWay />} />
            <Route path="/history" element={<History />} />
            <Route path="/replay/:id" element={<Replay />} />
            <Route path="/sources" element={<Sources />} />
            <Route path="/eval" element={<Evaluation />} />
            <Route path="/status" element={<Status />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="*" element={<div className="p-10 text-center">Page not found.</div>} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </SettingsProvider>
  </StrictMode>,
);
