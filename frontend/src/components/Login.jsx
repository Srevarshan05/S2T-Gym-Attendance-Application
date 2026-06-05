import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { auth as authApi } from "../api";

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [memberId, setMemberId] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      const tokenResponse = await authApi.login(memberId, password);
      login(tokenResponse);
      // Route by role
      if (tokenResponse.user.role === "admin") {
        navigate("/admin", { replace: true });
      } else {
        navigate("/dashboard", { replace: true });
      }
    } catch (err) {
      setError(err.message || "Login failed. Please check your credentials.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50 px-4 py-12">
      <div className="w-full max-w-[400px] bg-white flex flex-col space-y-6 p-6 shadow-xl border border-gray-100 rounded-3xl">
        {/* Header */}
        <div className="text-center mt-4">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-[#4ADE80]/10 text-[#4ADE80] mb-3">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h1 className="text-2xl font-black text-[#111827] tracking-tight">Welcome Back</h1>
          <p className="text-xs text-[#9CA3AF] mt-1">S2T Fitness Studio — Sign in to continue</p>
        </div>

        {/* Error banner */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-2xl px-4 py-3 flex items-start space-x-2">
            <svg className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-xs text-red-600 font-medium">{error}</p>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex flex-col space-y-4">
          {/* Member ID */}
          <div>
            <label htmlFor="login-identity" className="block text-xs font-semibold text-[#111827] mb-1.5 ml-1 uppercase tracking-wider">
              Member ID or Admin Email
            </label>
            <input
              id="login-identity"
              type="text"
              value={memberId}
              onChange={(e) => setMemberId(e.target.value)}
              placeholder="e.g. S2T101 or admin@s2tfitness.in"
              className="w-full px-5 py-3 rounded-full border border-gray-200 text-sm text-[#111827] placeholder-gray-400 focus:border-[#4ADE80] focus:ring-2 focus:ring-[#4ADE80]/20 transition-all outline-none"
              required
              autoComplete="username"
            />
          </div>

          {/* Password */}
          <div>
            <div className="flex justify-between items-center mb-1.5 px-1">
              <label htmlFor="login-password" className="block text-xs font-semibold text-[#111827] uppercase tracking-wider">
                Password
              </label>
            </div>
            <div className="relative">
              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-5 pr-12 py-3 rounded-full border border-gray-200 text-sm text-[#111827] placeholder-gray-400 focus:border-[#4ADE80] focus:ring-2 focus:ring-[#4ADE80]/20 transition-all outline-none"
                required
                autoComplete="current-password"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors p-1"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? (
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-[#4ADE80] text-[#111827] font-bold py-3.5 px-6 rounded-full hover:bg-[#3be074] hover:shadow-lg active:scale-95 transition-all duration-150 flex items-center justify-center space-x-2 mt-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            ) : (
              <>
                <span>Sign In</span>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              </>
            )}
          </button>
        </form>

        {/* Admin hint */}
        <div className="bg-gray-50 rounded-2xl p-3 border border-dashed border-gray-200">
          <p className="text-[10px] text-[#9CA3AF] text-center font-medium">
            <span className="font-bold text-[#111827]">Admin login:</span> admin@s2tfitness.in
          </p>
        </div>

        {/* Footer */}
        <div className="text-center pb-2">
          <p className="text-xs text-[#9CA3AF]">
            New member?{" "}
            <Link to="/register" className="font-bold text-[#111827] hover:text-[#4ADE80] transition-colors">
              Register here
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
