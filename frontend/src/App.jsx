import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import Login from "./components/Login";
import Register from "./components/Register";
import MemberDashboard from "./components/MemberDashboard";
import QRCheckin from "./components/QRCheckin";
import AdminDashboard from "./components/admin/AdminDashboard";

function ProtectedRoute({ children, requiredRole }) {
  const { isAuthenticated, isAdmin, isMember } = useAuth();
  if (!isAuthenticated) return <Navigate to="/" replace />;
  if (requiredRole === "admin" && !isAdmin) return <Navigate to="/dashboard" replace />;
  if (requiredRole === "member" && !isMember) return <Navigate to="/admin" replace />;
  return children;
}

export default function App() {
  const { isAuthenticated, isAdmin } = useAuth();

  return (
    <div className="min-h-screen bg-gray-100 font-sans">
      <Routes>
        {/* Public routes */}
        <Route
          path="/"
          element={
            isAuthenticated
              ? <Navigate to={isAdmin ? "/admin" : "/dashboard"} replace />
              : <Login />
          }
        />
        <Route
          path="/register"
          element={
            isAuthenticated
              ? <Navigate to={isAdmin ? "/admin" : "/dashboard"} replace />
              : <Register />
          }
        />

        {/* Member routes */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute requiredRole="member">
              <MemberDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/checkin"
          element={
            <ProtectedRoute requiredRole="member">
              <QRCheckin />
            </ProtectedRoute>
          }
        />

        {/* Admin routes */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute requiredRole="admin">
              <AdminDashboard />
            </ProtectedRoute>
          }
        />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
