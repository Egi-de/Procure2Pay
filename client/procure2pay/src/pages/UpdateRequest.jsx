import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { RequestAPI } from "../services/api.js";
import Button from "../components/Button";
import Input from "../components/Input";

const UpdateRequest = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const [form, setForm] = useState({
    title: "",
    description: "",
    amount: "",
    items: [{ description: "", quantity: 1, unit_price: "" }],
    proforma: null,
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchRequest = async () => {
      try {
        const response = await RequestAPI.detail(id);
        const request = response.data;
        setForm({
          title: request.title,
          description: request.description,
          amount: request.amount,
          items: request.items.map((item) => ({
            description: item.description,
            quantity: item.quantity,
            unit_price: item.unit_price,
          })),
          proforma: null, // Can't pre-fill file input
        });
      } catch (err) {
        console.error("Fetch request error:", err);
        setError("Failed to load request");
      } finally {
        setLoading(false);
      }
    };
    fetchRequest();
  }, [id]);

  const validateForm = () => {
    const errors = [];

    if (!form.title.trim()) {
      errors.push("Title is required.");
    }

    if (!form.description.trim()) {
      errors.push("Description is required.");
    }

    const amountNum = parseFloat(form.amount);
    if (!form.amount || isNaN(amountNum) || amountNum <= 0) {
      errors.push("Amount must be a positive number.");
    }

    if (form.items.length === 0) {
      errors.push("At least one item is required.");
    } else {
      form.items.forEach((item, index) => {
        if (!item.description.trim()) {
          errors.push(`Item ${index + 1} description is required.`);
        }
        const qtyNum = parseInt(item.quantity);
        if (isNaN(qtyNum) || qtyNum < 1) {
          errors.push(`Item ${index + 1} quantity must be at least 1.`);
        }
        const priceNum = parseFloat(item.unit_price);
        if (isNaN(priceNum) || priceNum <= 0) {
          errors.push(`Item ${index + 1} unit price must be positive.`);
        }
      });
    }

    return errors;
  };

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleItemChange = (index, field, value) => {
    setForm((prev) => {
      const items = prev.items.map((item, idx) =>
        idx === index ? { ...item, [field]: value } : item
      );
      return { ...prev, items };
    });
  };

  const addItem = () => {
    setForm((prev) => ({
      ...prev,
      items: [...prev.items, { description: "", quantity: 1, unit_price: "" }],
    }));
  };

  const removeItem = (index) => {
    setForm((prev) => ({
      ...prev,
      items: prev.items.filter((_, idx) => idx !== index),
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const errors = validateForm();
    if (errors.length > 0) {
      setError(errors);
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await RequestAPI.update(id, {
        title: form.title,
        description: form.description,
        amount: form.amount,
        proforma: form.proforma,
        items: form.items.map((item) => ({
          ...item,
          quantity: Number(item.quantity),
          unit_price: Number(item.unit_price),
        })),
      });
      navigate(`/requests/${id}`);
    } catch {
      setError("Unable to update request");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <section className="max-w-3xl mx-auto space-y-6">
        <div className="text-center">Loading...</div>
      </section>
    );
  }

  return (
    <section className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">
          Update request
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-300">
          Modify request details and line items.
        </p>
      </div>
      {error && (
        <div className="p-3 rounded-md bg-rose-50 dark:bg-rose-500/20 text-rose-600 dark:text-rose-100 text-sm">
          {Array.isArray(error) ? (
            <ul className="list-disc list-inside space-y-1">
              {error.map((msg, idx) => (
                <li key={idx}>{msg}</li>
              ))}
            </ul>
          ) : error.detail ? (
            error.detail
          ) : (
            "Please review the fields highlighted below."
          )}
        </div>
      )}
      <form
        className="space-y-6 bg-white/80 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-700 rounded-lg p-6 shadow-sm backdrop-blur"
        onSubmit={handleSubmit}
      >
        <div className="grid gap-6 sm:grid-cols-2">
          <label className="space-x-2">
            <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
              Title
            </span>
            <Input
              name="title"
              value={form.title}
              onChange={handleChange}
              required
              placeholder="Laptop purchase"
            />
          </label>
          <label className="space-x-2">
            <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
              Amount
            </span>
            <Input
              type="number"
              min="0"
              name="amount"
              value={form.amount}
              onChange={handleChange}
              required
            />
          </label>
        </div>
        <label className="space-y-4 block">
          <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
            Description
          </span>
          <textarea
            name="description"
            rows={3}
            value={form.description}
            onChange={handleChange}
            className="w-full border border-slate-200 dark:border-slate-700 rounded-md px-3 py-2 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
            placeholder="Describe business justification"
          />
        </label>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-200">
              Line items
            </p>
            <Button type="button" onClick={addItem} variant="link">
              Add item
            </Button>
          </div>
          {form.items.map((item, index) => (
            <div
              key={index}
              className="grid gap-3 sm:grid-cols-12 bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-md p-4"
            >
              <Input
                className="sm:col-span-6"
                placeholder="Description"
                value={item.description}
                onChange={(e) =>
                  handleItemChange(index, "description", e.target.value)
                }
                required
              />
              <Input
                className="sm:col-span-3"
                type="number"
                min="1"
                placeholder="Qty"
                value={item.quantity}
                onChange={(e) =>
                  handleItemChange(index, "quantity", e.target.value)
                }
                required
              />
              <Input
                className="sm:col-span-3"
                type="number"
                min="0"
                placeholder="Unit price"
                value={item.unit_price}
                onChange={(e) =>
                  handleItemChange(index, "unit_price", e.target.value)
                }
                required
              />
              {form.items.length > 1 && (
                <Button
                  className="sm:col-span-12"
                  type="button"
                  onClick={() => removeItem(index)}
                  variant="danger"
                >
                  Remove
                </Button>
              )}
            </div>
          ))}
        </div>

        <label className="block space-y-1">
          <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
            Vendor proforma (PDF or image) - Optional
          </span>
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            onChange={(event) =>
              setForm((prev) => ({ ...prev, proforma: event.target.files[0] }))
            }
            className="w-full border border-slate-200 dark:border-slate-700 rounded-md px-3 py-2 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 file:bg-slate-100 dark:file:bg-slate-700 file:border-0"
          />
        </label>

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 rounded-md bg-slate-900 text-white hover:bg-slate-700 dark:bg-slate-700 dark:hover:bg-slate-600 disabled:opacity-60"
          >
            {submitting ? "Updating..." : "Update request"}
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

export default UpdateRequest;
