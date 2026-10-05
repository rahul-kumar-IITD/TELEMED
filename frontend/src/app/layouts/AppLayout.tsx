import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { PATHS } from "../../config/routes";
import { useAuth } from "../../hooks/useAuth";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `text-white no-underline min-h-[44px] inline-flex items-center px-2 border-b-[3px] ${
    isActive ? "border-gold" : "border-transparent"
  }`;

export function AppLayout() {
  const { session, logout } = useAuth();
  const navigate = useNavigate();

  const onLogout = () => {
    logout();
    navigate(PATHS.login, { replace: true });
  };

  return (
    <>
      <header className="bg-teal text-white flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2">
        <span className="font-display text-xl font-bold mr-auto">Telemed</span>
        <nav aria-label="Primary" className="flex flex-wrap items-center gap-x-2">
          {session === null ? (
            <>
              <NavLink to={PATHS.login} className={linkClass}>
                Log in
              </NavLink>
              <NavLink to={PATHS.register} className={linkClass}>
                Register
              </NavLink>
            </>
          ) : (
            <>
              {session.role !== "DOCTOR" && (
                <NavLink to={PATHS.doctors} className={linkClass}>
                  Doctors
                </NavLink>
              )}
              {session.role === "DOCTOR" && (
                <NavLink to={PATHS.queue} className={linkClass}>
                  Queue
                </NavLink>
              )}
              {session.role === "ADMIN" && (
                <NavLink to={PATHS.adminUsers} className={linkClass}>
                  Users
                </NavLink>
              )}
              <button
                type="button"
                onClick={onLogout}
                className="text-white bg-transparent border-0 min-h-[44px] min-w-[44px] px-2 cursor-pointer"
              >
                Log out
              </button>
            </>
          )}
        </nav>
      </header>
      <main className="max-w-[1180px] mx-auto p-4">
        <Outlet />
      </main>
    </>
  );
}
