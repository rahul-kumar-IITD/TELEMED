import { Link } from "react-router-dom";
import { homeForRole, PATHS } from "../../../config/routes";
import { useAuth } from "../../../hooks/useAuth";

export function NotAllowedPage() {
  const { session } = useAuth();
  return (
    <section className="card max-w-[420px] mx-auto mt-6 text-center" aria-labelledby="h-na">
      <h1 id="h-na">Not allowed</h1>
      <p>Your account role does not have access to this page.</p>
      <Link className="btn" to={session ? homeForRole(session.role) : PATHS.login}>
        Go to my home
      </Link>
    </section>
  );
}
