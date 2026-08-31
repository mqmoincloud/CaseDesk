import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { apiCall, removeToken, setUnauthorisedHandler } from "../api";
import { buttonQuiet, muted, page } from "../ui";

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();

  // Who is logged in, asked of the server rather than kept in localStorage.
  // Anything stored in the browser can be edited by whoever is sitting at it,
  // so the role has to come from /me on every load.
  const [user, setUser] = useState(null);

  // The drawer is only real on phones; wider screens keep the sidebar open in
  // CSS. It closes on any navigation, including ones no Link fired - so the
  // path is held in state and compared during render, React's own answer to
  // resetting state when a prop changes.
  const [menuOpen, setMenuOpen] = useState(false);
  const [lastPath, setLastPath] = useState(location.pathname);

  if (lastPath !== location.pathname) {
    setLastPath(location.pathname);
    setMenuOpen(false);
  }

  // One place that reacts to an expired token, instead of every page having
  // its own copy. apiCall calls this whenever the API answers 401.
  useEffect(() => {
    setUnauthorisedHandler(() => navigate("/login"));
    return () => setUnauthorisedHandler(null);
  }, [navigate]);

  // Bumped by a page that changed something /me returns, so this asks again.
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    async function loadMe() {
      const res = await apiCall("GET", "/me");

      if (!res.ok) {
        removeToken();
        navigate("/login");
        return;
      }

      setUser(res.data);
    }

    loadMe();
  }, [navigate, refresh]);

  function handleLogout() {
    removeToken();
    navigate("/login");
  }

  // NavLink gives us isActive, so the section you are in is marked.
  function linkClass({ isActive }) {
    const base = "block px-3 py-2 rounded text-sm font-medium";
    return isActive
      ? `${base} bg-slate-900 text-white`
      : `${base} text-slate-600 hover:bg-slate-100 hover:text-slate-900`;
  }

  // Nothing renders until we know who this is, otherwise the admin-only pages
  // would flash past their guard while user is still null.
  if (!user) {
    return <p className={`${page} ${muted}`}>Loading...</p>;
  }

  return (

    <div className="flex h-screen overflow-hidden bg-slate-50">

      {menuOpen && (
        <div
          onClick={() => setMenuOpen(false)}
          className="fixed inset-0 z-30 bg-slate-900/40 md:hidden"
        />
      )}

      <nav
        className={
          "fixed inset-y-0 left-0 z-40 w-56 shrink-0 border-r border-slate-200 " +
          "bg-white p-4 flex flex-col gap-1 overflow-y-auto " +
          "transition-transform duration-200 md:static md:translate-x-0 " +
          (menuOpen ? "translate-x-0" : "-translate-x-full")
        }
      >
        <div className="flex items-center justify-between mb-4">
          <Link to="/clients" className="text-lg font-semibold px-3 py-2">
            CaseDesk
          </Link>

          <button
            onClick={() => setMenuOpen(false)}
            aria-label="Close menu"
            className="md:hidden px-3 py-2 text-slate-500 hover:text-slate-900"
          >
            ✕
          </button>
        </div>

        <NavLink to="/clients" className={linkClass}>Clients</NavLink>
        <NavLink to="/cases" className={linkClass}>Cases</NavLink>
        {user.role === "admin" && (
          <NavLink to="/staff" className={linkClass}>Staff</NavLink>
        )}

        <div className="mt-auto">
          <NavLink to="/profile" className={linkClass}>
            <span className="block truncate">{user.name} Profile</span>
            <span className="block text-xs font-normal opacity-70">
              {user.role}
            </span>
          </NavLink>
          <button onClick={handleLogout} className={`${buttonQuiet} w-full mt-2`}>
            Log out
          </button>
        </div>
      </nav>


      <div className="flex-1 min-w-0 flex flex-col">

        <header className="md:hidden flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-3">
          <button
            onClick={() => setMenuOpen(true)}
            aria-label="Open menu"
            className="p-2 -ml-2 text-slate-700 hover:text-slate-900"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <path
                d="M3 5h14M3 10h14M3 15h14"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </button>
          <span className="font-semibold text-slate-900">CaseDesk</span>
        </header>

 
        <main className="flex-1 min-w-0 overflow-y-auto">
          <Outlet context={{ ...user, reloadUser: () => setRefresh((n) => n + 1) }} />
        </main>
      </div>
    </div>
  );
}
