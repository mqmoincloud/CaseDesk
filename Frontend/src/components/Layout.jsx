import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";

import { removeToken } from "../api";
import { buttonQuiet } from "../ui";

export default function Layout() {
  const navigate = useNavigate();

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

  return (
    <div className="flex min-h-screen">
      <nav className="w-56 shrink-0 border-r border-slate-200 bg-white p-4 flex flex-col gap-1">
        <Link to="/clients" className="text-lg font-semibold px-3 py-2 mb-4">
          CaseDesk
        </Link>

        <NavLink to="/clients" className={linkClass}>Clients</NavLink>
        <NavLink to="/cases" className={linkClass}>Cases</NavLink>

        <button onClick={handleLogout} className={`${buttonQuiet} mt-auto`}>
          Log out
        </button>
      </nav>

      {/* Whichever page matched the route renders here. */}
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  );
}
