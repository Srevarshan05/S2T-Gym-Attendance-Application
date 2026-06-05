import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { attendance as attendanceApi, payments as paymentsApi, plans as plansApi, auth as authApi } from "../api";

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

export default function MemberDashboard() {
  const navigate = useNavigate();
  const { user, logout, refreshToken } = useAuth();

  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [calendar, setCalendar] = useState(null);
  const [calLoading, setCalLoading] = useState(true);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedSession, setSelectedSession] = useState(null);
  const [checkinLoading, setCheckinLoading] = useState(false);
  const [checkinMsg, setCheckinMsg] = useState(null);

  const [activeTab, setActiveTab] = useState("home");
  const [notification, setNotification] = useState(null);

  // Payment submission
  const [showPayModal, setShowPayModal] = useState(false);
  const [gymPlans, setGymPlans] = useState([]);
  const [selectedPlanId, setSelectedPlanId] = useState("");
  const [payLoading, setPayLoading] = useState(false);

  const triggerToast = (msg, type = "success") => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 4000);
  };

  // Load attendance calendar
  useEffect(() => {
    setCalLoading(true);
    attendanceApi.getCalendar(year, month)
      .then(setCalendar)
      .catch(() => triggerToast("Could not load attendance calendar", "error"))
      .finally(() => setCalLoading(false));
  }, [year, month]);

  // Load plans for payment modal
  useEffect(() => {
    plansApi.list().then((d) => {
      setGymPlans(d.plans || []);
      if (d.plans?.length) setSelectedPlanId(d.plans[0].id);
    });
  }, []);

  const handleCheckin = async () => {
    if (!selectedSession) return;
    setCheckinLoading(true);
    try {
      const result = await attendanceApi.checkin(selectedSession);
      setIsModalOpen(false);
      setSelectedSession(null);
      triggerToast(`Check-in logged for ${selectedSession === "FN" ? "Forenoon" : "Afternoon"}!`);
      // Refresh calendar
      const cal = await attendanceApi.getCalendar(year, month);
      setCalendar(cal);
    } catch (err) {
      setIsModalOpen(false);
      triggerToast(err.message || "Check-in failed", "error");
    } finally {
      setCheckinLoading(false);
    }
  };

  const handleSubmitPayment = async () => {
    if (!selectedPlanId) return;
    setPayLoading(true);
    try {
      await paymentsApi.submit(selectedPlanId);
      setShowPayModal(false);
      triggerToast("Payment declared! Admin will review and activate your membership.");
    } catch (err) {
      triggerToast(err.message || "Payment submission failed", "error");
    } finally {
      setPayLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await authApi.logout(refreshToken);
    } catch (_) {}
    logout();
    navigate("/", { replace: true });
  };

  const membershipStatus = user?.membership_status || "PENDING";
  const statusColor = membershipStatus === "ACTIVE"
    ? "bg-[#4ADE80]/15 text-[#111827]"
    : membershipStatus === "PENDING"
    ? "bg-[#FBBF24]/15 text-[#b27c00]"
    : "bg-[#EF4444]/15 text-[#EF4444]";

  const totalDays = calendar?.total_sessions ?? 0;
  const daysInMonth = new Date(year, month, 0).getDate();
  const attendedDays = calendar?.days?.length ?? 0;

  // Build quick lookup for attended days
  const attendedSet = new Set(calendar?.days?.map((d) => d.date) || []);

  return (
    <div className="flex items-start justify-center min-h-screen bg-gray-100 px-0 py-0 sm:py-8 sm:px-4">
      <div className="w-full max-w-[400px] min-h-screen sm:min-h-0 bg-[#F9FAFB] flex flex-col relative shadow-xl sm:border border-gray-100 sm:rounded-3xl overflow-hidden">

        {/* Toast */}
        {notification && (
          <div className={`absolute top-4 left-4 right-4 z-50 flex items-center p-3 rounded-xl shadow-lg border animate-fade-in-down ${
            notification.type === "error"
              ? "bg-red-50 border-red-200"
              : "bg-white border-gray-100"
          }`}>
            <div className={`flex-shrink-0 mr-2.5 w-7 h-7 rounded-full flex items-center justify-center ${
              notification.type === "error" ? "bg-red-100" : "bg-[#4ADE80]/15"
            }`}>
              <svg className={`w-4 h-4 ${notification.type === "error" ? "text-red-500" : "text-[#4ADE80]"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d={notification.type === "error" ? "M6 18L18 6M6 6l12 12" : "M5 13l4 4L19 7"} />
              </svg>
            </div>
            <p className="text-[11px] font-semibold text-[#111827] flex-1">{notification.msg}</p>
          </div>
        )}

        {/* Scrollable body */}
        <div className="flex-1 pb-24 overflow-y-auto">
          <div className="p-5 space-y-5">

            {/* Header */}
            <div className="flex items-center justify-between mt-2">
              <div>
                <h1 className="text-xl font-black text-[#111827] tracking-tight">Hello, {user?.full_name?.split(" ")[0] ?? "Member"} 👋</h1>
                <p className="text-xs text-[#9CA3AF] font-medium">ID: {user?.member_id}</p>
              </div>
              <button onClick={handleLogout}
                className="w-10 h-10 rounded-full bg-[#111827] text-white font-bold text-sm flex items-center justify-center border-2 border-white shadow-sm hover:bg-gray-800 transition-colors cursor-pointer"
                title="Logout">
                {(user?.full_name || "M").split(" ").map((n) => n[0]).join("").slice(0, 2)}
              </button>
            </div>

            {/* Membership Card */}
            <div className="bg-white rounded-3xl p-5 border border-gray-100 shadow-sm space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-[10px] uppercase tracking-wider font-bold text-[#9CA3AF]">Membership</p>
                  <h2 className="text-base font-extrabold text-[#111827] mt-0.5">{user?.plan_name ?? "—"}</h2>
                </div>
                <span className={`px-3 py-1 rounded-full text-[10px] font-black tracking-wider ${statusColor}`}>{membershipStatus}</span>
              </div>
              <div className="flex items-center space-x-2 text-xs text-[#9CA3AF]">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <span>
                  {user?.expiry_date
                    ? `Valid until ${new Date(user.expiry_date).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}`
                    : membershipStatus === "PENDING"
                    ? "Pending admin approval"
                    : "No active membership"}
                </span>
              </div>
              {membershipStatus !== "ACTIVE" && (
                <button onClick={() => setShowPayModal(true)}
                  className="w-full py-2.5 rounded-full text-xs font-bold bg-[#111827] text-white hover:bg-black hover:shadow-md active:scale-95 transition-all cursor-pointer flex items-center justify-center space-x-1.5">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>I've Paid — Notify Admin</span>
                </button>
              )}
            </div>

            {/* QR Attendance Quick Action */}
            <div className="relative">
              {membershipStatus === "ACTIVE" && (
                <div className="absolute inset-0 rounded-3xl bg-[#4ADE80]/20 animate-pulse blur-sm" />
              )}
              <button onClick={() => {
                if (membershipStatus !== "ACTIVE") {
                  triggerToast("Activate your membership to log attendance.", "error");
                  return;
                }
                setIsModalOpen(true);
              }}
                className={`w-full bg-white relative rounded-3xl p-6 border border-gray-100 shadow-sm flex items-center justify-between text-left transition-transform active:scale-[0.98] cursor-pointer ${membershipStatus !== "ACTIVE" ? "opacity-60" : ""}`}>
                <div className="space-y-1">
                  <p className="text-[10px] uppercase tracking-wider font-bold text-[#4ADE80]">Session Logging</p>
                  <h3 className="text-lg font-black text-[#111827] tracking-tight">Mark Today's Attendance</h3>
                  <p className="text-[11px] text-[#9CA3AF] font-medium">Select FN or AN session</p>
                </div>
                <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${membershipStatus === "ACTIVE" ? "bg-[#4ADE80]/10 text-[#4ADE80]" : "bg-gray-100 text-gray-400"}`}>
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                  </svg>
                </div>
              </button>
            </div>

            {/* Attendance Calendar */}
            <div className="bg-white rounded-3xl p-5 border border-gray-100 shadow-sm space-y-4">
              {/* Month nav */}
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-[#111827] uppercase tracking-wider">Attendance Calendar</h3>
                <div className="flex items-center space-x-2">
                  <button onClick={() => {
                    const d = new Date(year, month - 2);
                    setYear(d.getFullYear()); setMonth(d.getMonth() + 1);
                  }} className="text-[#9CA3AF] hover:text-[#111827] p-1 cursor-pointer">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
                  </button>
                  <span className="text-xs font-bold text-[#111827] min-w-[70px] text-center">{MONTHS[month - 1]} {year}</span>
                  <button onClick={() => {
                    const d = new Date(year, month);
                    setYear(d.getFullYear()); setMonth(d.getMonth() + 1);
                  }} className="text-[#9CA3AF] hover:text-[#111827] p-1 cursor-pointer">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                  </button>
                </div>
              </div>

              {/* Summary */}
              <div className="flex justify-between items-end">
                <div>
                  <p className="text-[10px] text-[#9CA3AF]">Days attended</p>
                  <p className="text-2xl font-black text-[#111827]">{attendedDays} <span className="text-xs font-semibold text-[#9CA3AF]">/ {daysInMonth}</span></p>
                </div>
                {calendar?.streak > 0 && (
                  <div className="text-right">
                    <p className="text-[10px] text-[#9CA3AF]">Current streak</p>
                    <p className="text-2xl font-black text-[#4ADE80]">{calendar.streak} <span className="text-xs font-semibold text-[#9CA3AF]">days</span></p>
                  </div>
                )}
              </div>

              {/* Progress bar */}
              <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                <div className="h-full bg-[#4ADE80] rounded-full transition-all duration-500"
                  style={{ width: `${Math.min((attendedDays / daysInMonth) * 100, 100)}%` }} />
              </div>

              {/* Calendar grid */}
              {calLoading ? (
                <div className="text-center py-4 text-xs text-[#9CA3AF]">Loading...</div>
              ) : (
                <div className="grid grid-cols-7 gap-1">
                  {["Su","Mo","Tu","We","Th","Fr","Sa"].map((d) => (
                    <div key={d} className="text-center text-[9px] font-bold text-[#9CA3AF] py-1">{d}</div>
                  ))}
                  {Array.from({ length: new Date(year, month - 1, 1).getDay() }).map((_, i) => (
                    <div key={`e-${i}`} />
                  ))}
                  {Array.from({ length: daysInMonth }).map((_, i) => {
                    const day = i + 1;
                    const dateStr = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
                    const dayData = calendar?.days?.find((d) => d.date === dateStr);
                    const hasAny = !!dayData;
                    const hasBoth = dayData?.fn && dayData?.an;
                    return (
                      <div key={day} className={`aspect-square flex items-center justify-center rounded-full text-[10px] font-bold transition-all ${
                        hasBoth ? "bg-[#4ADE80] text-[#111827]"
                        : hasAny ? "bg-[#4ADE80]/40 text-[#111827]"
                        : "text-[#9CA3AF]"
                      }`}>
                        {day}
                      </div>
                    );
                  })}
                </div>
              )}
              <p className="text-[9px] text-[#9CA3AF] text-center">
                <span className="inline-block w-2 h-2 rounded-full bg-[#4ADE80] mr-1"></span>Both sessions
                <span className="inline-block w-2 h-2 rounded-full bg-[#4ADE80]/40 mr-1 ml-3"></span>One session
              </p>
            </div>
          </div>
        </div>

        {/* Session Modal */}
        {isModalOpen && (
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm z-40 flex flex-col justify-end">
            <div className="flex-1" onClick={() => setIsModalOpen(false)} />
            <div className="bg-white rounded-t-3xl p-6 space-y-5 shadow-2xl max-w-[400px] w-full mx-auto animate-slide-up">
              <div className="w-12 h-1 bg-gray-200 rounded-full mx-auto" />
              <div>
                <h3 className="text-lg font-black text-[#111827]">Select Session</h3>
                <p className="text-xs text-[#9CA3AF]">Choose your current workout session</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                {[
                  { key: "FN", label: "Forenoon (FN)", sub: "Morning Session", time: "5:00 AM – 12:00 PM" },
                  { key: "AN", label: "Afternoon (AN)", sub: "Evening Session", time: "4:00 PM – 10:00 PM" },
                ].map(({ key, label, sub, time }) => (
                  <button key={key} onClick={() => setSelectedSession(key)}
                    className={`p-4 rounded-2xl border text-left flex flex-col justify-between transition-all cursor-pointer ${
                      selectedSession === key ? "border-[#4ADE80] bg-[#4ADE80]/5 ring-2 ring-[#4ADE80]/20" : "border-gray-200 hover:border-gray-300"
                    }`}>
                    <div>
                      <h4 className="text-sm font-bold text-[#111827]">{label}</h4>
                      <p className="text-[10px] text-[#9CA3AF] mt-0.5">{sub}</p>
                    </div>
                    <span className="text-[10px] font-semibold text-[#111827] mt-4">{time}</span>
                  </button>
                ))}
              </div>
              <button onClick={handleCheckin} disabled={!selectedSession || checkinLoading}
                className="w-full bg-[#4ADE80] text-[#111827] font-bold py-3.5 rounded-full hover:bg-[#3be074] hover:shadow-lg active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center cursor-pointer">
                {checkinLoading ? (
                  <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                ) : "Confirm Attendance"}
              </button>
              <button onClick={() => { setIsModalOpen(false); setSelectedSession(null); }}
                className="w-full py-2 text-center text-xs font-bold text-[#9CA3AF] hover:text-[#111827] cursor-pointer">
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Pay Modal */}
        {showPayModal && (
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm z-40 flex flex-col justify-end">
            <div className="flex-1" onClick={() => setShowPayModal(false)} />
            <div className="bg-white rounded-t-3xl p-6 space-y-5 shadow-2xl max-w-[400px] w-full mx-auto animate-slide-up">
              <div className="w-12 h-1 bg-gray-200 rounded-full mx-auto" />
              <div>
                <h3 className="text-lg font-black text-[#111827]">Declare Payment</h3>
                <p className="text-xs text-[#9CA3AF]">Select the plan you've paid for. Admin will verify and activate.</p>
              </div>
              <select value={selectedPlanId} onChange={(e) => setSelectedPlanId(e.target.value)}
                className="w-full px-4 py-3 rounded-full border border-gray-200 text-sm text-[#111827] focus:border-[#4ADE80] focus:ring-2 focus:ring-[#4ADE80]/20 outline-none">
                {gymPlans.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} — Rs.{parseFloat(p.price).toLocaleString()}
                  </option>
                ))}
              </select>
              <button onClick={handleSubmitPayment} disabled={payLoading}
                className="w-full bg-[#111827] text-white font-bold py-3.5 rounded-full hover:bg-black transition-all disabled:opacity-50 cursor-pointer">
                {payLoading ? "Submitting..." : "Notify Admin"}
              </button>
              <button onClick={() => setShowPayModal(false)} className="w-full py-2 text-xs font-bold text-[#9CA3AF] hover:text-[#111827] cursor-pointer">Cancel</button>
            </div>
          </div>
        )}

        {/* Bottom Nav */}
        <div className="absolute bottom-0 left-0 right-0 h-20 bg-white border-t border-gray-100 px-6 flex items-center justify-around z-30 sm:rounded-b-3xl">
          {[
            { key: "home", label: "Home", path: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" },
            { key: "checkin", label: "Check In", path: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" },
            { key: "history", label: "History", path: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" },
          ].map(({ key, label, path }) => (
            <button key={key} onClick={() => {
              if (key === "checkin") { if (membershipStatus === "ACTIVE") setIsModalOpen(true); else triggerToast("Active membership required", "error"); }
              else setActiveTab(key);
            }}
              className={`flex flex-col items-center space-y-1 w-14 cursor-pointer transition-colors ${activeTab === key ? "text-[#4ADE80]" : "text-[#9CA3AF] hover:text-[#111827]"}`}>
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={path} />
              </svg>
              <span className="text-[9px] font-bold uppercase tracking-wide">{label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
