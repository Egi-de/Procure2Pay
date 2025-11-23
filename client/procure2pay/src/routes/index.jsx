import { Routes, Route } from "react-router-dom";
import { NotificationProvider } from "../context/NotificationContext";
import ProtectedRoute from "../components/ProtectedRoute";
import Layout from "../components/Layout";
import Login from "../pages/Login";
import Dashboard from "../pages/Dashboard";
import RequestList from "../pages/RequestList";
import CreateRequest from "../pages/CreateRequest";
import UpdateRequest from "../pages/UpdateRequest";
import DetailView from "../pages/DetailView";
import ReceiptUpload from "../pages/ReceiptUpload";
import Unauthorized from "../pages/Unauthorized";

const AppRoutes = () => {
  return (
    <NotificationProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/unauthorized" element={<Unauthorized />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout>
                <Dashboard />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/requests"
          element={
            <ProtectedRoute>
              <Layout>
                <RequestList />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/create-request"
          element={
            <ProtectedRoute>
              <Layout>
                <CreateRequest />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/update-request/:id"
          element={
            <ProtectedRoute>
              <Layout>
                <UpdateRequest />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/detail-view/:id"
          element={
            <ProtectedRoute>
              <Layout>
                <DetailView />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/receipt-upload/:id"
          element={
            <ProtectedRoute>
              <Layout>
                <ReceiptUpload />
              </Layout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </NotificationProvider>
  );
};

export default AppRoutes;
