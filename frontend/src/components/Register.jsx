import React, { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { plans as plansApi, auth as authApi } from "../api";
import { useAuth } from "../context/AuthContext";

export default function Register() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [gymPlans, setGymPlans] = useState([]);
  const [plansLoading, setPlansLoading] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(null); // { memberId, planName }

  const [form, setForm] = useState({
    full_name: "",
    age: "",
    gender: "Male",
    phone: "",
    email: "",
    address: "",
    password: "",
    plan_id: "",
  });
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    plansApi.list()
      .then((data) => {
        setGymPlans(data.plans || []);
        if (data.plans && data.plans.length > 0) {
          setForm((f) => ({ ...f, plan_id: data.plans[0].id }));
        }
      })
      .catch(() => setError("Could not load gym plans. Please refresh."))
      .finally(() => setPlansLoading(false));
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      const payload = { ...form, age: parseInt(form.age, 10) };
      const registerResult = await authApi.register(payload);
      setSuccess({ memberId: registerResult.member_id, planName: registerResult.plan_name });
    } catch (err) {
      setError(err.message || "Registration failed. Please check all fields.");
    } finally {
      setIsLoading(false);
    }
  };

  // Success screen
  if (success) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50 px-4 py-12">
        <div className="w-full max-w-[400px] bg-white flex flex-col items-center space-y-6 p-8 shadow-xl border border-gray-100 rounded-3xl text-center">
          <div className="w-16 h-16 rounded-full bg-[#4ADE80]/10 flex items-center justify-center">
            <svg className="w-8 h-8 text-[#4ADE80]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <div>
            <h2 className="text-xl font-black text-[#111827]">Registration Successful!</h2>
            <p className="text-xs text-[#9CA3AF] mt-1">Save your Member ID — you'll need it to log in</p>
          </div>
          <div className="w-full bg-[#4ADE80]/10 border border-[#4ADE80]/30 rounded-2xl p-4">
            <p className="text-[10px] text-[#9CA3AF] uppercase tracking-widest font-bold mb-1">Your Member ID</p>
            <p className="text-3xl font-black text-[#111827] tracking-widest">{success.memberId}</p>
            <p className="text-[10px] text-[#9CA3AF] mt-1">Plan: {success.planName} • Status: Pending Approval</p>
          </div>
          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-3 w-full">
            <p className="text-xs text-amber-700 font-medium">
              Your membership is <strong>pending admin approval</strong>. You can log in now and notify the admin once you've paid.
            </p>
          </div>
          <Link
            to="/"
            className="w-full bg-[#111827] text-white font-bold py-3.5 rounded-full hover:bg-black transition-all text-sm text-center"
          >
            Go to Login with {success.memberId}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50 px-4 py-12">
      <div className="w-full max-w-[400px] bg-white flex flex-col space-y-5 p-6 shadow-xl border border-gray-100 rounded-3xl">
        {/* Header */}
        <div className="text-center mt-2">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-[#4ADE80]/10 text-[#4ADE80] mb-3">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
            </svg>
          </div>
          <h1 className="text-2xl font-black text-[#111827] tracking-tight">Join S2T Fitness</h1>
          <p className="text-xs text-[#9CA3AF] mt-1">Create your member account</p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-2xl px-4 py-3 flex items-start space-x-2">
            <svg className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1">
              {error.includes(" | ") ? (
                <ul className="space-y-0.5">
                  {error.split(" | ").map((msg, i) => (
                    <li key={i} className="text-xs text-red-600 font-medium capitalize">• {msg}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-red-600 font-medium">{error}</p>
              )}
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col space-y-3">
          {/* Full Name */}
          <div>
            <label className="block text-xs font-semibold text-[#111827] mb-1 ml-1 uppercase tracking-wider">Full Name</label>
            <input name="full_name" value={form.full_name} onChange={handleChange} required placeholder="Rahul Sharma"
              className="w-full px-4 py-3 rounded-full border border-gray-200 text-sm text-[#111827] placeholder-gray-400 focus:border-[#4ADE80] focus:ring-2 focus:ring-[#4ADE80]/20 outline-none transition-all" />
          </div>

          {/* Age + Gender row */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-[#111827] mb-1 ml-1 uppercase tracking-wider">Age</label>
              <input name="age" type="number" min="10" max="100" value={form.age} onChange={handleChange} required placeholder="25"
                className="w-full px-4 py-3 rounded-full border border-gray-200 text-sm text-[#111827] placeholder-gray-400 focus:border-[#4ADE80] focus:ring-2 focus:ring-[#4ADE80]/20 outline-none transition-all" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[#111827] mb-1 ml-1 uppercase tracking-wider">Gender</label>
              <select name="gender" value={form.gender} onChange={handleChange}
                className="w-full px-4 py-3 rounded-full border border-gray-200 text-sm text-[#111827] focus:border-[#4ADE80] focus:ring-2 focus:ring-[#4ADE80]/20 outline-none transition-all appearance-none bg-white">
                <option>Male</option>
                <option>Female</option>
                <option>Other</option>
              </select>
            </div>
          </div>

          {/* Phone */}
          <div>
            <label className="block text-xs font-semibold text-[#111827] mb-1 ml-1 uppercase tracking-wider">Phone (10 digits)</label>
            <input name="phone" type="tel" maxLength={10} value={form.phone} onChange={handleChange} required placeholder="9876543210"
              className="w-full px-4 py-3 rounded-full border border-gray-200 text-sm text-[#111827] placeholder-gray-400 focus:border-[#4ADE80] focus:ring-2 focus:ring-[#4ADE80]/20 outline-none transition-all" />
          </div>

          {/* Email */}
          <div>
            <label className="block text-xs font-semibold text-[#111827] mb-1 ml-1 uppercase tracking-wider">Email</label>
            <input name="email" type="email" value={form.email} onChange={handleChange} required placeholder="rahul@example.com"
              className="w-full px-4 py-3 rounded-full border border-gray-200 text-sm text-[#111827] placeholder-gray-400 focus:border-[#4ADE80] focus:ring-2 focus:ring-[#4ADE80]/20 outline-none transition-all" />
          </div>

          {/* Address */}
          <div>
            <label className="block text-xs font-semibold text-[#111827] mb-1 ml-1 uppercase tracking-wider">Address</label>
            <textarea name="address" value={form.address} onChange={handleChange} required placeholder="12, Anna Nagar, Trichy - 620001" rows={2}
              className="w-full px-4 py-3 rounded-2xl border border-gray-200 text-sm text-[#111827] placeholder-gray-400 focus:border-[#4ADE80] focus:ring-2 focus:ring-[#4ADE80]/20 outline-none transition-all resize-none" />
          </div>

          {/* Plan */}
          <div>
            <label className="block text-xs font-semibold text-[#111827] mb-1 ml-1 uppercase tracking-wider">Gym Plan</label>
            {plansLoading ? (
              <div className="w-full px-4 py-3 rounded-full border border-gray-200 text-sm text-[#9CA3AF]">Loading plans...</div>
            ) : (
              <select name="plan_id" value={form.plan_id} onChange={handleChange} required
                className="w-full px-4 py-3 rounded-full border border-gray-200 text-sm text-[#111827] focus:border-[#4ADE80] focus:ring-2 focus:ring-[#4ADE80]/20 outline-none transition-all appearance-none bg-white">
                {gymPlans.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} — Rs.{parseFloat(p.price).toLocaleString()}{p.duration_days ? ` / ${p.duration_days} days` : " (Custom)"}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Password */}
          <div>
            <label className="block text-xs font-semibold text-[#111827] mb-1 ml-1 uppercase tracking-wider">Password</label>
            <div className="relative">
              <input name="password" type={showPassword ? "text" : "password"} value={form.password} onChange={handleChange} required
                placeholder="Min 8 chars, A-Z, a-z, 0-9"
                className="w-full pl-4 pr-12 py-3 rounded-full border border-gray-200 text-sm text-[#111827] placeholder-gray-400 focus:border-[#4ADE80] focus:ring-2 focus:ring-[#4ADE80]/20 outline-none transition-all" />
              <button type="button" onClick={() => setShowPassword(!showPassword)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 p-1">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d={showPassword ? "M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
                      : "M15 12a3 3 0 11-6 0 3 3 0 016 0zM2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"} />
                </svg>
              </button>
            </div>
          </div>

          <button type="submit" disabled={isLoading || plansLoading}
            className="w-full bg-[#4ADE80] text-[#111827] font-bold py-3.5 px-6 rounded-full hover:bg-[#3be074] hover:shadow-lg active:scale-95 transition-all flex items-center justify-center space-x-2 mt-2 disabled:opacity-50 disabled:cursor-not-allowed">
            {isLoading ? (
              <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            ) : (
              <span>Create Account</span>
            )}
          </button>
        </form>

        <div className="text-center pb-2">
          <p className="text-xs text-[#9CA3AF]">
            Already have an account?{" "}
            <Link to="/" className="font-bold text-[#111827] hover:text-[#4ADE80] transition-colors">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
