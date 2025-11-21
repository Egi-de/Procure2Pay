const ReceiptValidationModal = ({ validation, onClose }) => {
  if (!validation) return null;
  const mismatches = validation.mismatches || {};

  return (
    <div className="fixed inset-0 bg-slate-900/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-slate-900">
            Receipt validation
          </h3>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-900"
          >
            Close
          </button>
        </div>
        <div
          className={`p-4 rounded-md text-sm ${
            validation.is_valid
              ? "bg-emerald-50 text-emerald-700"
              : "bg-rose-50 text-rose-700"
          }`}
        >
          {validation.is_valid
            ? "Receipt matches the purchase order."
            : "Discrepancies detected."}
        </div>
        {!validation.is_valid && (
          <div className="space-y-2 text-sm max-h-64 overflow-y-auto">
            {Object.entries(mismatches).map(([key, value]) => (
              <div key={key} className="border border-rose-100 rounded-md p-3">
                <p className="font-medium text-rose-700 capitalize">{key}</p>
                {typeof value === "string" ? (
                  <p className="text-slate-700 text-xs">{value}</p>
                ) : (
                  <>
                    <p className="text-slate-700 text-xs">
                      Expected: {value.expected}
                    </p>
                    <p className="text-slate-700 text-xs">
                      Actual: {value.actual}
                    </p>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ReceiptValidationModal;
