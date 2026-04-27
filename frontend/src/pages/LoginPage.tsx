import { FormEvent, useState } from "react";
import { LogIn } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export function LoginPage() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password, username.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-panel">
        <div>
          <p className="eyebrow">Grid Chat</p>
          <h1>{mode === "login" ? "Welcome back" : "Create your account"}</h1>
        </div>
        <div className="segmented">
          <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>
            Login
          </button>
          <button
            className={mode === "register" ? "active" : ""}
            onClick={() => setMode("register")}
          >
            Register
          </button>
        </div>
        <form onSubmit={submit} className="stack">
          {mode === "register" && (
            <label>
              Username
              <input
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="sshah"
                minLength={1}
                maxLength={80}
                required
              />
            </label>
          )}
          <label>
            Email
            <input
              type={mode === "login" ? "text" : "email"}
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder={mode === "login" ? "username or email" : "you@example.com"}
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              minLength={8}
              required
            />
          </label>
          {error && <p className="error">{error}</p>}
          <button className="primary" disabled={loading}>
            <LogIn size={18} />
            {loading ? "Working..." : mode === "login" ? "Login" : "Register"}
          </button>
        </form>
      </section>
    </main>
  );
}
