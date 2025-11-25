import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import Button from "../components/Button";
import Input from "../components/Input";
import Form from "../components/Form";

const Login = () => {
  const navigate = useNavigate();
  const { login, error, user } = useAuth();
  const [form, setForm] = useState({ username: "", password: "" });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);

  const handleChange = (event) => {
    setForm((prev) => ({
      ...prev,
      [event.target.name]: event.target.value,
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setFormError(null);
    try {
      await login(form);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setFormError(err.response?.data?.detail || "Login failed");
    } finally {
      setSubmitting(false);
    }
  };

  useEffect(() => {
    if (user) {
      navigate("/dashboard", { replace: true });
    }
  }, [user, navigate]);

  return (
    <section className="min-h-screen flex flex-col items-center justify-center bg-slate-50 dark:bg-slate-900 px-4 transition-colors">
      <div className="w-full max-w-md bg-white/90 dark:bg-slate-900/60 backdrop-blur rounded-lg border border-slate-200 dark:border-slate-800 shadow-lg p-6 space-y-6 transition-colors">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">
            Procure2Pay Portal
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-300">
            Sign in to manage procurement workflows.
          </p>
        </div>
        {(formError || error) && (
          <div className="p-3 text-sm rounded-md bg-rose-50 dark:bg-rose-500/20 text-rose-600 dark:text-rose-100">
            {formError || error}
          </div>
        )}
        <form className="space-y-4" onSubmit={handleSubmit}>
          <label className="block space-y-1">
            <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
              Username
            </span>
            <input
              type="text"
              name="username"
              value={form.username}
              onChange={handleChange}
              className="w-full border border-slate-200 dark:border-slate-700 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:focus:ring-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
              placeholder="egide.dev"
              required
            />
          </label>
          <label className="block space-y-1">
            <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
              Password
            </span>
            <input
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              className="w-full border border-slate-200 dark:border-slate-700 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:focus:ring-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
              placeholder="••••••••"
              required
            />
          </label>
          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2 rounded-md bg-slate-900 text-white hover:bg-slate-700 dark:bg-slate-700 dark:hover:bg-slate-600 disabled:opacity-60 transition-colors"
          >
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </section>
  );
};

export default Login;
