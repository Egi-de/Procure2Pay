import { Link } from "react-router-dom";

const Unauthorized = () => (
  <section className="min-h-screen flex flex-col items-center justify-center gap-4">
    <h1 className="text-3xl font-semibold text-rose-500">Access denied</h1>
    <p className="text-slate-600 max-w-md text-center">
      You do not have permissions to view this page. Use an account with the
      right role or go back to your dashboard.
    </p>
    <Link
      to="/"
      className="px-4 py-2 bg-slate-900 text-white rounded-md hover:bg-slate-700"
    >
      Go home
    </Link>
  </section>
);

export default Unauthorized;

