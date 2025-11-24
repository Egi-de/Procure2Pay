import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { RequestAPI } from "../services/api.js";

const ReceiptUpload = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!file) {
      setError("Select a receipt file first");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await RequestAPI.submitReceipt(id, file);
      navigate(`/detail-view/${id}`);
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to upload receipt");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="max-w-lg space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">
          Submit receipt
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-300">
          Upload the final receipt for automated validation.
        </p>
      </div>
      {error && (
        <div className="p-3 rounded-md bg-rose-50 dark:bg-rose-500/20 text-rose-700 dark:text-rose-100 text-sm">
          {error}
        </div>
      )}
      <form
        onSubmit={handleSubmit}
        className="bg-white/80 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-700 rounded-lg p-6 space-y-4 backdrop-blur"
      >
        <input
          type="file"
          accept=".pdf,.png,.jpg,.jpeg"
          onChange={(event) => setFile(event.target.files[0])}
          className="w-full border border-slate-200 dark:border-slate-700 rounded-md px-3 py-2 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 file:bg-slate-100 dark:file:bg-slate-700 file:border-0"
        />
        {submitting && (
          <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
            <div className="bg-slate-900 dark:bg-slate-100 h-2 rounded-full"></div>
          </div>
        )}
        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 rounded-md bg-slate-900 text-white disabled:opacity-50 hover:bg-slate-700 dark:bg-slate-700 dark:hover:bg-slate-600"
          >
            {submitting ? "Uploading..." : "Upload"}
          </button>
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="px-4 py-2 rounded-md border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/60"
          >
            Cancel
          </button>
        </div>
      </form>
    </section>
  );
};

export default ReceiptUpload;
