import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { RequestAPI } from "../services/api.js";
import Button from "../components/Button";
import { toast } from "react-toastify";

const StatusBadge = ({ status }) => {
  const styles = {
    PENDING:
      "bg-amber-100 text-amber-800 dark:bg-amber-400/20 dark:text-amber-100",
    APPROVED:
      "bg-emerald-100 text-emerald-700 dark:bg-emerald-400/20 dark:text-emerald-100",
    REJECTED:
      "bg-rose-100 text-rose-700 dark:bg-rose-400/20 dark:text-rose-100",
  };
  return (
    <span
      className={`px-2 py-1 rounded-full text-xs font-semibold transition-colors ${
        styles[status] ||
        "bg-slate-100 text-slate-600 dark:bg-slate-700/60 dark:text-slate-200"
      }`}
    >
      {status}
    </span>
  );
};

const Dashboard = () => {
  const { user } = useAuth();
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const isStaff = user?.role === "STAFF";
  const isApprover = user?.role?.startsWith("APPROVER");

  const loadRequests = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (isApprover) {
        params.status = "PENDING";
      }
      const { data } = await RequestAPI.list(params);
      setRequests(data.results ?? data);
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to load requests");
      console.error("Load requests error:", err);
    } finally {
      setLoading(false);
    }
  }, [isApprover]);

  useEffect(() => {
    loadRequests();
  }, [loadRequests]);

  const summary = useMemo(() => {
    const base = {
      total: requests.length,
      pending: 0,
      approved: 0,
      rejected: 0,
    };
    return requests.reduce(
      (acc, req) => {
        const key = req.status.toLowerCase();
        if (acc[key] !== undefined) {
          acc[key] += 1;
        }
        return acc;
      },
      { ...base }
    );
  }, [requests]);

  const handleDecision = async (id, action, comment = "") => {
    try {
      if (action === "approve") {
        await RequestAPI.approve(id, { comment });
        toast.success("Request approved successfully");
      } else {
        await RequestAPI.reject(id, { comment });
        toast.success("Request rejected successfully");
      }
      await loadRequests();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Unable to update request");
    }
  };

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">
            {isApprover ? "Approval queue" : "My requests"}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-300">
            Track purchase requests, approvals, and receipts in one place.
          </p>
        </div>
        {isStaff && (
          <Link
            to="/requests/create"
            className="inline-flex items-center justify-center px-4 py-2 rounded-md bg-slate-900 text-white hover:bg-slate-700 dark:bg-white/10 dark:text-white dark:hover:bg-white/20"
          >
            New request
          </Link>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {["pending", "approved", "rejected"].map((key) => (
          <div
            key={key}
            className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-transparent backdrop-blur-sm p-4 shadow-sm transition-colors"
          >
            <p className="text-sm text-slate-500 dark:text-slate-300 capitalize">
              {key}
            </p>
            <p className="text-3xl font-semibold text-slate-900 dark:text-white">
              {summary[key]}
            </p>
          </div>
        ))}
      </div>

      <div className="bg-white/80 dark:bg-transparent border border-slate-200 dark:border-slate-700 rounded-lg shadow-sm overflow-hidden backdrop-blur">
        <div className="p-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
          <p className="font-medium text-slate-800 dark:text-slate-100">
            Requests
          </p>
          <button
            onClick={loadRequests}
            className="text-sm text-slate-500 dark:text-slate-300 hover:text-slate-800 dark:hover:text-white"
          >
            Refresh
          </button>
        </div>
        {loading ? (
          <div className="p-6 text-center text-slate-500 dark:text-slate-300">
            Loading...
          </div>
        ) : error ? (
          <div className="p-6 text-center text-rose-600 dark:text-rose-300">
            {error}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-100 dark:divide-slate-800">
              <thead className="bg-slate-50 dark:bg-slate-900/30 text-left text-xs font-semibold text-slate-500 dark:text-slate-300">
                <tr>
                  <th className="px-4 py-3">Title</th>
                  <th className="px-4 py-3">Amount</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Created</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-sm">
                {requests.map((request) => (
                  <tr
                    key={request.id}
                    className="hover:bg-slate-50 dark:hover:bg-slate-900/40 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <Link
                        to={`/requests/${request.id}`}
                        className="font-medium text-slate-900 dark:text-slate-100 hover:text-blue-600 dark:hover:text-blue-300"
                      >
                        {request.title}
                      </Link>
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        Level {request.current_approval_level}/
                        {request.required_approval_levels}
                      </p>
                    </td>
                    <td className="px-4 py-3 font-semibold text-slate-900 dark:text-slate-100">
                      ${Number(request.amount).toFixed(2)}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={request.status} />
                    </td>
                    <td className="px-4 py-3 text-slate-500 dark:text-slate-400">
                      {new Date(request.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2 text-sm">
                        {isApprover && request.status === "PENDING" ? (
                          <>
                            <Button
                              onClick={() =>
                                handleDecision(request.id, "approve")
                              }
                              variant="success"
                            >
                              Approve
                            </Button>
                            <Button
                              onClick={() => {
                                const reason = prompt("Reason for rejection?");
                                if (reason !== null) {
                                  handleDecision(request.id, "reject", reason);
                                }
                              }}
                              variant="danger"
                            >
                              Reject
                            </Button>
                          </>
                        ) : (
                          <Link
                            to={`/requests/${request.id}`}
                            className="px-3 py-1 rounded-md border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/60"
                          >
                            View
                          </Link>
                        )}
                        {isStaff && request.status === "APPROVED" && (
                          <Link
                            to={`/requests/${request.id}/receipt`}
                            className="px-3 py-1 rounded-md border border-blue-200 text-blue-600 hover:bg-blue-50 dark:border-blue-500/40 dark:text-blue-200 dark:hover:bg-blue-500/10"
                          >
                            Submit receipt
                          </Link>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {!requests.length && (
                  <tr>
                    <td
                      className="px-4 py-6 text-center text-slate-500 dark:text-slate-400"
                      colSpan={5}
                    >
                      No requests yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
};

export default Dashboard;
