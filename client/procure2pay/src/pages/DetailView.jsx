import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { RequestAPI } from "../services/api.js";
import ReceiptValidationModal from "./ReceiptValidationModal.jsx";

const InfoBlock = ({ label, children }) => (
  <div>
    <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
    <div className="text-base text-slate-900">{children}</div>
  </div>
);

const DetailView = () => {
  const { id } = useParams();
  const { user } = useAuth();
  const [request, setRequest] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showValidation, setShowValidation] = useState(false);

  const isApprover = user?.role?.startsWith("APPROVER");
  const isStaff = user?.role === "STAFF";

  const loadRequest = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await RequestAPI.detail(id);
      setRequest(data);
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to load request");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadRequest();
  }, [loadRequest]);

  const handleDecision = async (action) => {
    try {
      if (action === "approve") {
        await RequestAPI.approve(id, {});
      } else {
        const reason = prompt("Provide rejection reason");
        if (reason === null) return;
        await RequestAPI.reject(id, { comment: reason });
      }
      await loadRequest();
    } catch (err) {
      alert(err.response?.data?.detail || "Unable to update request");
    }
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div className="text-rose-600">{error}</div>;
  }

  if (!request) {
    return null;
  }

  const WORKFLOW_ROLES = ["APPROVER_L1", "APPROVER_L2"];
  const nextRequiredRole = request.current_approval_level
    ? WORKFLOW_ROLES[request.current_approval_level - 1]
    : null;

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4">
        <h1 className="text-2xl font-semibold text-slate-900">
          {request.title}
        </h1>
        <div className="grid gap-4 sm:grid-cols-3 bg-white border border-slate-200 rounded-lg p-4">
          <InfoBlock label="Status">{request.status}</InfoBlock>
          <InfoBlock label="Amount">
            ${Number(request.amount).toFixed(2)}
          </InfoBlock>
          <InfoBlock label="Created by">
            {request.created_by?.first_name || request.created_by?.username}
          </InfoBlock>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-3">
          <h2 className="font-semibold text-slate-900">Summary</h2>
          <p className="text-sm text-slate-600">
            {request.description || "N/A"}
          </p>
          <div className="space-y-2">
            <p className="text-sm font-medium text-slate-700">Line items</p>
            <ul className="space-y-2 text-sm">
              {request.items.map((item) => (
                <li
                  key={item.id}
                  className="flex items-center justify-between border border-slate-100 rounded-md px-3 py-2"
                >
                  <div>
                    <p className="font-medium text-slate-900">
                      {item.description}
                    </p>
                    <p className="text-xs text-slate-500">
                      Qty {item.quantity} · $
                      {Number(item.unit_price).toFixed(2)}
                    </p>
                  </div>
                  <p className="font-semibold text-slate-900">
                    $
                    {(
                      Number(item.quantity || 0) * Number(item.unit_price || 0)
                    ).toFixed(2)}
                  </p>
                </li>
              ))}
            </ul>
          </div>

          <div className="space-y-2 text-sm">
            <p className="text-sm font-medium text-slate-700">Documents</p>
            <div className="flex flex-wrap gap-3">
              {request.proforma && (
                <a
                  href={request.proforma}
                  target="_blank"
                  rel="noreferrer"
                  className="text-blue-600 hover:underline"
                >
                  View proforma
                </a>
              )}
              {request.purchase_order && (
                <a
                  href={request.purchase_order}
                  target="_blank"
                  rel="noreferrer"
                  className="text-blue-600 hover:underline"
                >
                  Download PO
                </a>
              )}
              {request.receipt && (
                <a
                  href={request.receipt}
                  target="_blank"
                  rel="noreferrer"
                  className="text-blue-600 hover:underline"
                >
                  View receipt
                </a>
              )}
            </div>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-slate-900">Approval history</h2>
            {isApprover &&
              request.status === "PENDING" &&
              user?.role === nextRequiredRole && (
                <div className="flex gap-2">
                  <button
                    onClick={() => handleDecision("approve")}
                    className="px-3 py-1 rounded-md bg-emerald-100 text-emerald-700"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => handleDecision("reject")}
                    className="px-3 py-1 rounded-md bg-rose-100 text-rose-700"
                  >
                    Reject
                  </button>
                </div>
              )}
          </div>
          <div className="space-y-2">
            {request.approvals.map((step) => (
              <div
                key={step.id}
                className="border border-slate-100 rounded-md px-3 py-2 text-sm flex justify-between"
              >
                <div>
                  <p className="font-medium text-slate-900">
                    Level {step.level}: {step.decision}
                  </p>
                  <p className="text-xs text-slate-500">
                    {step.approver?.first_name ||
                      step.approver?.username ||
                      "Pending"}
                  </p>
                </div>
                <p className="text-xs text-slate-500">
                  {step.decided_at
                    ? new Date(step.decided_at).toLocaleString()
                    : "Awaiting decision"}
                </p>
              </div>
            ))}
          </div>

          {request.receipt_validation?.is_valid !== undefined && (
            <button
              onClick={() => setShowValidation(true)}
              className="text-sm text-blue-600 hover:underline"
            >
              View receipt validation
            </button>
          )}
        </div>
      </div>

      {isStaff && request.status === "APPROVED" && !request.receipt && (
        <Link
          to={`/requests/${request.id}/receipt`}
          className="inline-flex px-4 py-2 rounded-md bg-blue-600 text-white hover:bg-blue-500"
        >
          Submit receipt
        </Link>
      )}

      {showValidation && (
        <ReceiptValidationModal
          validation={request.receipt_validation}
          onClose={() => setShowValidation(false)}
        />
      )}
    </section>
  );
};

export default DetailView;
