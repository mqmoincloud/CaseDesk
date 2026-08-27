import { Navigate, Route, Routes } from "react-router-dom";

import { getToken } from "./api";
import Layout from "./components/Layout";
import CaseDetail from "./pages/CaseDetail";
import Cases from "./pages/Cases";
import ClientDetail from "./pages/ClientDetail";
import Clients from "./pages/Clients";
import EditClient from "./pages/EditClient";
import Login from "./pages/Login";
import NewCase from "./pages/NewCase";
import NewClient from "./pages/NewClient";
import Register from "./pages/Register";

// Routes re-runs this on every navigation, so the token is read fresh each
// time. Reading it in App instead would only happen on the first render, and
// logging in would not be noticed until the page was reloaded by hand.
function Protected() {
  return getToken() ? <Layout /> : <Navigate to="/login" />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Everything inside here shares the sidebar, and the login check is
          written once instead of on every single route. */}
      <Route element={<Protected />}>
        <Route path="/clients" element={<Clients />} />
        <Route path="/clients/new" element={<NewClient />} />
        <Route path="/clients/:id" element={<ClientDetail />} />
        <Route path="/clients/:id/edit" element={<EditClient />} />
        <Route path="/cases" element={<Cases />} />
        <Route path="/cases/new" element={<NewCase />} />
        <Route path="/cases/:id" element={<CaseDetail />} />
      </Route>

      <Route path="*" element={<Navigate to="/clients" />} />
    </Routes>
  );
}
