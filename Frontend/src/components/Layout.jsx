import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";

import { removeToken } from "../api";

export default function Layout() {
  const navigate = useNavigate();

  function handleLogout() {
    removeToken();
    navigate("/login");
  }

  // NavLink gives us isActive, so the section you are in is marked.
  function linkClass({ isActive }) {
    return isActive ? "block p-2 bg-gray-200" : "block p-2";
  }

  return (
    <div className="flex min-h-screen">
      <nav className="w-48 border-r p-4 flex flex-col">
        <Link to="/clients" className="text-xl mb-6">CaseDesk</Link>

        <NavLink to="/clients" className={linkClass}>Clients</NavLink>
        <NavLink to="/cases" className={linkClass}>Cases</NavLink>

        <button onClick={handleLogout} className="mt-auto border p-2">
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
