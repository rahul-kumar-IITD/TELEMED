import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "../../../api/client";
import { AriaLiveRegion } from "../../../components/AriaLiveRegion";
import { FormField } from "../../../components/FormField";
import { LoadingState } from "../../../components/LoadingState";
import { homeForRole, MESSAGES, PATHS } from "../../../config/routes";
import { useAuth } from "../../../hooks/useAuth";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const notice = (location.state as { notice?: string } | null)?.notice;
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (busy) return;
    setError("");
    if (!email.trim() || !password) {
      setError(MESSAGES.invalidCredentials);
      return;
    }
    setBusy(true);
    try {
      const s = await login({ email: email.trim(), password });
      navigate(homeForRole(s.role), { replace: true });
    } catch (err) {
      setBusy(false);
      if (err instanceof ApiError && err.status === 401) setError(MESSAGES.invalidCredentials);
      else setError(err instanceof ApiError ? err.userMessage : MESSAGES.generic);
    }
  };

  return (
    <section className="card max-w-[420px] mx-auto mt-6" aria-labelledby="h-login">
      <p className="font-display text-[2.2rem] leading-[1.1] text-teal m-0 mb-2">Care, from wherever you are.</p>
      <h1 id="h-login">Log in</h1>
      <AriaLiveRegion assertive>
        {error ? <div className="msg msg-err">{error}</div> : null}
      </AriaLiveRegion>
      <AriaLiveRegion>{notice ? <div className="msg msg-info">{notice}</div> : null}</AriaLiveRegion>
      <form onSubmit={onSubmit} noValidate>
        <FormField
          id="login-email"
          label="Email"
          type="email"
          autoComplete="username"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <FormField
          id="login-password"
          label="Password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <p className="mt-3.5">
          <button className="btn w-full" type="submit" disabled={busy}>
            Log in
          </button>
        </p>
      </form>
      {busy ? <LoadingState label="Logging in..." /> : null}
      <p className="text-sm text-ink2">
        New here? <Link to={PATHS.register}>Create an account</Link>
      </p>
    </section>
  );
}
