import { Link } from "react-router-dom";
import { homeForRole, PATHS } from "../../../config/routes";
import { useAuth } from "../../../hooks/useAuth";

export function NotFoundPage() {
  const { session } = useAuth();
  return (
    <section className="card max-w-[420px] mx-auto mt-6 text-center" aria-labelledby="h-nf">
      <h1 id="h-nf">Page not found</h1>
      <p>This page, or the record you tried to open, does not exist or is not yours.</p>
      <Link className="btn" to={session ? homeForRole(session.role) : PATHS.login}>
        Go to my home
      </Link>
    </section>
  );
}
