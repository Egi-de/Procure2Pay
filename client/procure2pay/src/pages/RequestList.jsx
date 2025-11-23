import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { RequestAPI } from "../services/api";
import { useNotifications } from "../context/NotificationContext";
import Button from "../components/Button";
import Form from "../components/Form";
import Input from "../components/Input";
import LoadingSpinner from "../components/LoadingSpinner";

const RequestList = () => {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const { addNotification } = useNotifications();

  const fetchRequests = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {
        status: statusFilter || undefined,
        search: searchTerm || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      };
      const response = await RequestAPI.list({ ...params, page_size: 50 });
      setRequests(response.data.results || []);
    } catch (err) {
      const userMessage = err.userMessage || "Failed to fetch requests";
      setError(userMessage);
      addNotification(userMessage, "error");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, searchTerm, dateFrom, dateTo, addNotification]);

  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]);

  const handleStatusChange = (e) => {
    setStatusFilter(e.target.value);
  };

  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
  };

  const handleDateFromChange = (e) => {
    setDateFrom(e.target.value);
  };

  const handleDateToChange = (e) => {
    setDateTo(e.target.value);
  };

  const statusOptions = [
    { value: "", label: "All Statuses" },
    { value: "pending", label: "Pending" },
    { value: "approved", label: "Approved" },
    { value: "rejected", label: "Rejected" },
  ];

  if (loading) {
    return (
      <div
        className="flex justify-center items-center min-h-screen"
        role="status"
        aria-label="Loading requests"
      >
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="p-4 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-4" role="heading" aria-level="1">
        Requests
      </h1>
      <div className="mb-6 space-y-4">
        <Form
          onSubmit={(e) => {
            e.preventDefault();
            fetchRequests();
          }}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Input
              label="Search by Title/Description"
              type="text"
              value={searchTerm}
              onChange={handleSearchChange}
              placeholder="Enter search term..."
              id="search"
            />
            <Input
              label="Filter by Status"
              type="select"
              value={statusFilter}
              onChange={handleStatusChange}
              options={statusOptions}
              id="status"
            />
            <Input
              label="From Date"
              type="date"
              value={dateFrom}
              onChange={handleDateFromChange}
              id="dateFrom"
            />
            <Input
              label="To Date"
              type="date"
              value={dateTo}
              onChange={handleDateToChange}
              id="dateTo"
            />
          </div>
          <div className="flex justify-end mt-4">
            <Button type="submit" loading={loading}>
              Filter
            </Button>
          </div>
        </Form>
      </div>
      {error && (
        <div
          className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-md dark:bg-red-900 dark:border-red-600 dark:text-red-100"
          role="alert"
          aria-live="assertive"
        >
          Error: {error}
        </div>
      )}
      <div className="overflow-x-auto">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {requests.length > 0 ? (
            requests.map((request) => (
              <article
                key={request.id}
                className="bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow dark:bg-gray-800"
                role="article"
                aria-label={`Request: ${request.title}`}
              >
                <h2 className="text-xl font-semibold mb-2">{request.title}</h2>
                <p className="text-gray-600 mb-3 dark:text-gray-300">
                  {request.description}
                </p>
                <p className="text-sm text-gray-500 mb-4 dark:text-gray-400">
                  Status:{" "}
                  <span
                    className={`capitalize px-2 py-1 rounded-full text-xs font-medium ${
                      request.status === "approved"
                        ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100"
                        : request.status === "rejected"
                        ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100"
                        : "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100"
                    }`}
                  >
                    {request.status}
                  </span>
                </p>
                {request.created_at && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
                    Created: {new Date(request.created_at).toLocaleDateString()}
                  </p>
                )}
                <Link
                  to={`/detail-view/${request.id}`}
                  className="block w-full text-center"
                  aria-label={`View details for ${request.title}`}
                >
                  <Button variant="primary" size="sm" className="w-full">
                    View Details
                  </Button>
                </Link>
              </article>
            ))
          ) : (
            <p
              className="col-span-full text-center text-gray-500 dark:text-gray-400"
              role="status"
            >
              No requests found matching the criteria.
            </p>
          )}
        </div>
      </div>
      {requests.length > 0 && (
        <div className="mt-6 flex justify-center">
          <Button
            onClick={fetchRequests}
            variant="secondary"
            disabled={loading}
          >
            Refresh List
          </Button>
        </div>
      )}
    </div>
  );
};

export default RequestList;
