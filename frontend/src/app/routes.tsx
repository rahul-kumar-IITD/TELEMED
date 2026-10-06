import type { ReactNode } from "react";
import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { homeForRole, PATHS } from "../config/routes";
import { useAuth } from "../hooks/useAuth";
import type { Role } from "../types/contracts";
import { AppLayout } from "./layouts/AppLayout";
import { LoginPage } from "./pages/auth/LoginPage";
import { RegisterPage } from "./pages/auth/RegisterPage";
import { BookingConfirmationPage } from "./pages/patient/BookingConfirmationPage";
import { DoctorDetailPage } from "./pages/patient/DoctorDetailPage";
import { DoctorSearchPage } from "./pages/patient/DoctorSearchPage";
import { ResourceShell } from "./pages/shell/ResourceShell";
import { NotAllowedPage } from "./pages/system/NotAllowedPage";
import { NotFoundPage } from "./pages/system/NotFoundPage";

/** Unauthenticated -> /login; wrong role -> not-allowed page (URL unchanged). */
function RequireRole({ roles }: { roles?: Role[] }) {
  const { session } = useAuth();
  if (!session) return <Navigate to={PATHS.login} replace />;
  if (roles && !roles.includes(session.role)) return <NotAllowedPage />;
  return <Outlet />;
}

/** Logged-in users never see the auth screens; they go to their role home. */
function PublicOnly({ children }: { children: ReactNode }) {
  const { session } = useAuth();
  return session ? <Navigate to={homeForRole(session.role)} replace /> : <>{children}</>;
}

function RootRedirect() {
  const { session } = useAuth();
  return <Navigate to={session ? homeForRole(session.role) : PATHS.login} replace />;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<RootRedirect />} />
        <Route path="login" element={<PublicOnly><LoginPage /></PublicOnly>} />
        <Route path="register" element={<PublicOnly><RegisterPage /></PublicOnly>} />

        <Route element={<RequireRole />}>
          <Route path="doctors" element={<DoctorSearchPage />} />
          <Route path="doctors/:doctor_id" element={<DoctorDetailPage />} />
          <Route path="doctors/:doctor_id/book/:slot_id" element={<BookingConfirmationPage />} />
        </Route>
        <Route element={<RequireRole roles={["DOCTOR"]} />}>
          <Route
            path="queue"
            element={<ResourceShell title="Daily queue" path="/api/doctors/me/queue" emptyMessage="No appointments today." />}
          />
        </Route>
        <Route element={<RequireRole roles={["ADMIN"]} />}>
          <Route
            path="admin/users"
            element={<ResourceShell title="Users" path="/api/admin/users" emptyMessage="No users found." />}
          />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
