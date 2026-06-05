import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { attendance as attendanceApi } from "../api";

export default function QRCheckin() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [selectedSession, setSelectedSession] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null); // { success, message }

  const handleCheckin = async () => {
    if (!selectedSession) return;
    setLoading(true);
    try {
      const data = await attendanceApi.checkin(selectedSession);
      setResult({
        success: true,
        message: `Attendance logged for ${selectedSession === "FN" ? "Forenoon (Morning)" : "Afternoon (Evening)"} session!`,
        data,
      });
    } catch (err) {
      setResult({ success: false, message: err.message || "Check-in failed." });
    } finally {
      setLoading(false);
    }
  };

  if (result) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50 px-4">
        <div className="w-full max-w-[400px] bg-white rounded-3xl p-8 shadow-xl border border-gray-100 text-center space-y-5">
          <div className={`w-16 h-16 rounded-full mx-auto flex items-center justify-center ${result.success ? "bg-[#4ADE80]/10" : "bg-red-100"}`}>
            <svg className={`w-8 h-8 ${result.success ? "text-[#4ADE80]" : "text-red-500"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5}
                d={result.success ? "M5 13l4 4L19 7" : "M6 18L18 6M6 6l12 12"} />
            </svg>
          </div>
          <div>
            <h2 className={`text-xl font-black ${result.success ? "text-[#111827]" : "text-red-600"}`}>
              {result.success ? "Check-In Successful!" : "Check-In Failed"}
            </h2>
            <p className="text-sm text-[#9CA3AF] mt-2">{result.message}</p>
          </div>
          {result.success && (
            <div className="bg-gray-50 rounded-2xl p-4 border border-gray-100 text-left">
              <p className="text-[10px] uppercase tracking-wider font-bold text-[#9CA3AF] mb-1">Session logged</p>
              <p className="text-sm font-bold text-[#111827]">{selectedSession === "FN" ? "Forenoon (FN)" : "Afternoon (AN)"}</p>
              <p className="text-xs text-[#9CA3AF]">{new Date().toLocaleDateString("en-IN", { weekday: "long", day: "2-digit", month: "long", year: "numeric" })}</p>
            </div>
          )}
          <button onClick={() => navigate("/dashboard")}
            className="w-full bg-[#111827] text-white font-bold py-3.5 rounded-full hover:bg-black transition-all cursor-pointer">
            Back to Dashboard
          </button>
          {!result.success && (
            <button onClick={() => setResult(null)}
              className="w-full text-xs font-bold text-[#9CA3AF] hover:text-[#111827] py-2 cursor-pointer">
              Try Again
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50 px-4">
      <div className="w-full max-w-[400px] bg-white rounded-3xl p-6 shadow-xl border border-gray-100 space-y-6">
        {/* Header */}
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-[#4ADE80]/10 text-[#4ADE80] mb-3">
            <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
          </div>
          <h1 className="text-2xl font-black text-[#111827]">Gym Check-In</h1>
          <p className="text-xs text-[#9CA3AF] mt-1">
            {user?.full_name} · {user?.member_id}
          </p>
          <p className="text-[11px] text-[#9CA3AF] mt-1">
            {new Date().toLocaleDateString("en-IN", { weekday: "long", day: "2-digit", month: "long" })}
          </p>
        </div>

        {/* Session selector */}
        <div>
          <p className="text-xs font-semibold text-[#111827] mb-3 uppercase tracking-wider text-center">Select Your Session</p>
          <div className="grid grid-cols-2 gap-4">
            {[
              { key: "FN", label: "Forenoon", sub: "Morning Session", time: "5:00 AM – 12:00 PM" },
              { key: "AN", label: "Afternoon", sub: "Evening Session", time: "4:00 PM – 10:00 PM" },
            ].map(({ key, label, sub, time }) => (
              <button key={key} onClick={() => setSelectedSession(key)}
                className={`p-5 rounded-2xl border-2 text-left flex flex-col justify-between min-h-[120px] transition-all cursor-pointer ${
                  selectedSession === key
                    ? "border-[#4ADE80] bg-[#4ADE80]/5 ring-2 ring-[#4ADE80]/20"
                    : "border-gray-200 hover:border-gray-300"
                }`}>
                <div>
                  <h4 className="text-base font-black text-[#111827]">{label}</h4>
                  <p className="text-[10px] text-[#9CA3AF] mt-0.5">{sub}</p>
                </div>
                <span className="text-[10px] font-semibold text-[#111827] mt-3">{time}</span>
              </button>
            ))}
          </div>
        </div>

        <button onClick={handleCheckin} disabled={!selectedSession || loading}
          className="w-full bg-[#4ADE80] text-[#111827] font-bold py-4 rounded-full hover:bg-[#3be074] hover:shadow-lg active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center text-sm cursor-pointer">
          {loading ? (
            <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          ) : (
            "Confirm Attendance"
          )}
        </button>

        <button onClick={() => navigate("/dashboard")}
          className="w-full text-xs font-bold text-[#9CA3AF] hover:text-[#111827] py-1 cursor-pointer text-center">
          Back to Dashboard
        </button>
      </div>
    </div>
  );
}
