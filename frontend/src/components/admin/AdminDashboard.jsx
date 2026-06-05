import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { dashboard as dashApi, members as membersApi, payments as paymentsApi, reports as reportsApi } from "../../api";
import QRGenerator from "./QRGenerator";

const TABS = [
  { key: "overview", label: "Overview", icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" },
  { key: "members", label: "Members", icon: "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" },
  { key: "payments", label: "Payments", icon: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" },
  { key: "reports", label: "Reports", icon: "M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" },
];

const STATUS_COLORS = {
  ACTIVE: "bg-[#4ADE80]/15 text-[#166534]",
  PENDING: "bg-amber-100 text-amber-800",
  EXPIRED: "bg-red-100 text-red-700",
  SUSPENDED: "bg-gray-100 text-gray-600",
};

function KpiCard({ label, value, sub, accent }) {
  return (
    <div className={`bg-white rounded-2xl p-4 border shadow-sm ${accent ? "border-[#4ADE80]/30 bg-[#4ADE80]/5" : "border-gray-100"}`}>
      <p className="text-[10px] uppercase tracking-widest font-bold text-[#9CA3AF]">{label}</p>
      <p className={`text-3xl font-black mt-1 ${accent ? "text-[#111827]" : "text-[#111827]"}`}>{value}</p>
      {sub && <p className="text-[10px] text-[#9CA3AF] mt-0.5">{sub}</p>}
    </div>
  );
}

// ── Overview Tab ──────────────────────────────────────────────────────────────
function OverviewTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    dashApi.getOverview()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex-1 flex items-center justify-center text-[#9CA3AF] text-sm">Loading dashboard...</div>;
  if (error) return <div className="p-4 text-red-500 text-sm">{error}</div>;
  if (!data) return null;

  return (
    <div className="space-y-5">
      {/* Membership KPIs */}
      <div>
        <p className="text-[10px] uppercase tracking-widest font-bold text-[#9CA3AF] mb-2">Membership</p>
        <div className="grid grid-cols-2 gap-3">
          <KpiCard label="Total Members" value={data.total_members} accent />
          <KpiCard label="Active" value={data.active_members} sub="Members" />
          <KpiCard label="Pending" value={data.pending_members} sub="Awaiting approval" />
          <KpiCard label="Expired" value={data.expired_members} sub="Lapsed memberships" />
        </div>
      </div>

      {/* Today's attendance */}
      <div>
        <p className="text-[10px] uppercase tracking-widest font-bold text-[#9CA3AF] mb-2">Today's Attendance</p>
        <div className="grid grid-cols-3 gap-3">
          <KpiCard label="FN" value={data.today_fn_count} sub="Forenoon" />
          <KpiCard label="AN" value={data.today_an_count} sub="Afternoon" />
          <KpiCard label="Unique" value={data.today_unique_members} sub="Members" />
        </div>
      </div>

      {/* Revenue */}
      <div>
        <p className="text-[10px] uppercase tracking-widest font-bold text-[#9CA3AF] mb-2">Revenue — {data.current_month_label}</p>
        <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm">
          <p className="text-[10px] text-[#9CA3AF]">Total Collected</p>
          <p className="text-3xl font-black text-[#111827]">
            Rs.{parseFloat(data.monthly_revenue).toLocaleString("en-IN")}
          </p>
          {data.pending_payments_count > 0 && (
            <div className="mt-3 bg-amber-50 border border-amber-200 rounded-xl p-2.5 flex items-center space-x-2">
              <svg className="w-4 h-4 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-xs text-amber-700 font-semibold">{data.pending_payments_count} payment{data.pending_payments_count > 1 ? "s" : ""} awaiting approval</p>
            </div>
          )}
        </div>
      </div>

      {/* Expiring Soon */}
      {data.expiring_soon?.length > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-widest font-bold text-[#9CA3AF] mb-2">Expiring Soon</p>
          <div className="space-y-2">
            {data.expiring_soon.map((m) => (
              <div key={m.member_id} className="bg-white rounded-2xl px-4 py-3 border border-orange-100 shadow-sm flex items-center justify-between">
                <div>
                  <p className="text-sm font-bold text-[#111827]">{m.full_name}</p>
                  <p className="text-[10px] text-[#9CA3AF]">{m.member_id} · {m.plan_name}</p>
                </div>
                <span className={`text-xs font-black px-2 py-1 rounded-full ${m.days_remaining <= 2 ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"}`}>
                  {m.days_remaining === 0 ? "Today" : `${m.days_remaining}d left`}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Members Tab ───────────────────────────────────────────────────────────────
function MembersTab() {
  const [membersData, setMembersData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState(null); // member detail modal
  const [statusUpdate, setStatusUpdate] = useState("");
  const [updating, setUpdating] = useState(false);
  const [toast, setToast] = useState("");

  const loadMembers = useCallback(() => {
    setLoading(true);
    membersApi.list(page, 15, search)
      .then(setMembersData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [page, search]);

  useEffect(() => { loadMembers(); }, [loadMembers]);

  const handleUpdateStatus = async () => {
    if (!selected || !statusUpdate) return;
    setUpdating(true);
    try {
      await membersApi.update(selected.member_id, { membership_status: statusUpdate });
      setToast(`Status updated to ${statusUpdate}`);
      setSelected(null);
      loadMembers();
    } catch (e) {
      setToast(e.message);
    } finally {
      setUpdating(false);
      setTimeout(() => setToast(""), 3000);
    }
  };

  const handleDeactivate = async (memberId) => {
    if (!confirm(`Deactivate member ${memberId}? They will no longer be able to log in.`)) return;
    try {
      await membersApi.deactivate(memberId);
      setToast(`Member ${memberId} deactivated`);
      setSelected(null);
      loadMembers();
    } catch (e) {
      setToast(e.message);
    } finally {
      setTimeout(() => setToast(""), 3000);
    }
  };

  return (
    <div className="space-y-4">
      {toast && <div className="bg-[#4ADE80]/10 border border-[#4ADE80]/30 rounded-xl p-3 text-xs font-bold text-[#111827]">{toast}</div>}

      {/* Search */}
      <div className="relative">
        <svg className="w-4 h-4 text-[#9CA3AF] absolute left-3.5 top-1/2 -translate-y-1/2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          placeholder="Search by name or ID..."
          className="w-full pl-9 pr-4 py-2.5 rounded-full border border-gray-200 text-sm text-[#111827] placeholder-gray-400 focus:border-[#4ADE80] focus:ring-2 focus:ring-[#4ADE80]/20 outline-none" />
      </div>

      {loading ? (
        <div className="text-center py-8 text-[#9CA3AF] text-sm">Loading members...</div>
      ) : (
        <>
          <div className="space-y-2">
            {membersData?.members?.length === 0 && (
              <p className="text-center text-[#9CA3AF] text-sm py-8">No members found.</p>
            )}
            {membersData?.members?.map((m) => (
              <button key={m.id} onClick={() => { setSelected(m); setStatusUpdate(m.membership_status); }}
                className="w-full bg-white rounded-2xl px-4 py-3.5 border border-gray-100 shadow-sm flex items-center justify-between text-left hover:border-gray-200 transition-all cursor-pointer">
                <div>
                  <p className="text-sm font-bold text-[#111827]">{m.full_name}</p>
                  <p className="text-[10px] text-[#9CA3AF]">{m.member_id} · {m.plan_name} · Age {m.age}</p>
                </div>
                <div className="flex flex-col items-end space-y-1">
                  <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${STATUS_COLORS[m.membership_status] || "bg-gray-100 text-gray-600"}`}>
                    {m.membership_status}
                  </span>
                  {m.days_remaining != null && <p className="text-[9px] text-[#9CA3AF]">{m.days_remaining}d left</p>}
                </div>
              </button>
            ))}
          </div>

          {/* Pagination */}
          {membersData && membersData.total_pages > 1 && (
            <div className="flex items-center justify-between pt-2">
              <button disabled={page === 1} onClick={() => setPage(p => p - 1)}
                className="text-xs font-bold text-[#9CA3AF] hover:text-[#111827] disabled:opacity-40 cursor-pointer">← Prev</button>
              <span className="text-xs text-[#9CA3AF]">Page {page} of {membersData.total_pages}</span>
              <button disabled={page === membersData.total_pages} onClick={() => setPage(p => p + 1)}
                className="text-xs font-bold text-[#9CA3AF] hover:text-[#111827] disabled:opacity-40 cursor-pointer">Next →</button>
            </div>
          )}
        </>
      )}

      {/* Member Detail Modal */}
      {selected && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-end justify-center p-4">
          <div className="bg-white rounded-3xl p-6 w-full max-w-[400px] space-y-4 shadow-2xl animate-slide-up">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-black text-[#111827]">{selected.full_name}</h3>
                <p className="text-xs text-[#9CA3AF]">{selected.member_id} · {selected.email}</p>
              </div>
              <button onClick={() => setSelected(null)} className="text-[#9CA3AF] hover:text-[#111827] p-1 cursor-pointer">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              {[["Phone", selected.phone], ["Age", selected.age], ["Gender", selected.gender], ["Plan", selected.plan_name]].map(([k, v]) => (
                <div key={k} className="bg-gray-50 rounded-xl p-2.5">
                  <p className="text-[9px] uppercase tracking-wider text-[#9CA3AF] font-bold">{k}</p>
                  <p className="font-bold text-[#111827] mt-0.5">{v}</p>
                </div>
              ))}
            </div>
            {/* Status update */}
            <div>
              <p className="text-xs font-bold text-[#111827] mb-2 uppercase tracking-wider">Change Status</p>
              <div className="grid grid-cols-2 gap-2">
                {["ACTIVE", "PENDING", "EXPIRED", "SUSPENDED"].map((s) => (
                  <button key={s} onClick={() => setStatusUpdate(s)}
                    className={`py-2 rounded-full text-xs font-bold border transition-all cursor-pointer ${statusUpdate === s ? "bg-[#111827] text-white border-[#111827]" : "bg-white text-[#9CA3AF] border-gray-200 hover:border-gray-300"}`}>
                    {s}
                  </button>
                ))}
              </div>
              <button onClick={handleUpdateStatus} disabled={updating || statusUpdate === selected.membership_status}
                className="w-full mt-3 bg-[#4ADE80] text-[#111827] font-bold py-3 rounded-full hover:bg-[#3be074] transition-all disabled:opacity-50 cursor-pointer text-sm">
                {updating ? "Updating..." : "Update Status"}
              </button>
            </div>
            {selected.is_active && (
              <button onClick={() => handleDeactivate(selected.member_id)}
                className="w-full py-2.5 rounded-full border border-red-200 text-red-500 text-xs font-bold hover:bg-red-50 transition-all cursor-pointer">
                Deactivate Account
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Payments Tab ──────────────────────────────────────────────────────────────
function PaymentsTab() {
  const [pending, setPending] = useState([]);
  const [loading, setLoading] = useState(true);
  const [rejectModal, setRejectModal] = useState(null);
  const [rejectReason, setRejectReason] = useState("");
  const [processing, setProcessing] = useState(null);
  const [toast, setToast] = useState("");

  const loadPending = () => {
    setLoading(true);
    paymentsApi.getPending()
      .then((d) => setPending(d.requests || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadPending(); }, []);

  const showToast = (msg) => { setToast(msg); setTimeout(() => setToast(""), 4000); };

  const handleApprove = async (payment) => {
    setProcessing(payment.id);
    try {
      await paymentsApi.approve(payment.id);
      showToast(`Approved! ${payment.full_name}'s membership is now ACTIVE.`);
      loadPending();
    } catch (e) {
      showToast(e.message);
    } finally {
      setProcessing(null);
    }
  };

  const handleReject = async () => {
    if (!rejectModal || !rejectReason.trim()) return;
    setProcessing(rejectModal.id);
    try {
      await paymentsApi.reject(rejectModal.id, rejectReason);
      showToast(`Rejected: ${rejectModal.full_name}'s payment request.`);
      setRejectModal(null);
      setRejectReason("");
      loadPending();
    } catch (e) {
      showToast(e.message);
    } finally {
      setProcessing(null);
    }
  };

  return (
    <div className="space-y-4">
      {toast && <div className="bg-[#4ADE80]/10 border border-[#4ADE80]/30 rounded-xl p-3 text-xs font-bold text-[#111827]">{toast}</div>}

      {loading ? (
        <div className="text-center py-8 text-[#9CA3AF] text-sm">Loading pending payments...</div>
      ) : pending.length === 0 ? (
        <div className="text-center py-12 space-y-2">
          <div className="w-12 h-12 rounded-full bg-[#4ADE80]/10 flex items-center justify-center mx-auto">
            <svg className="w-6 h-6 text-[#4ADE80]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="text-sm font-bold text-[#111827]">All caught up!</p>
          <p className="text-xs text-[#9CA3AF]">No pending payment approvals</p>
        </div>
      ) : (
        <div className="space-y-3">
          {pending.map((p) => (
            <div key={p.id} className="bg-white rounded-2xl p-4 border border-amber-100 shadow-sm space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-bold text-[#111827]">{p.full_name}</p>
                  <p className="text-[10px] text-[#9CA3AF]">{p.member_id} · {p.plan_name}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-black text-[#111827]">Rs.{parseFloat(p.amount).toLocaleString()}</p>
                  <p className="text-[10px] text-[#9CA3AF]">{new Date(p.submitted_at).toLocaleDateString("en-IN")}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <button onClick={() => handleApprove(p)} disabled={processing === p.id}
                  className="py-2.5 rounded-full bg-[#4ADE80] text-[#111827] text-xs font-bold hover:bg-[#3be074] transition-all disabled:opacity-50 cursor-pointer flex items-center justify-center space-x-1">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                  <span>{processing === p.id ? "..." : "Approve"}</span>
                </button>
                <button onClick={() => { setRejectModal(p); setRejectReason(""); }} disabled={processing === p.id}
                  className="py-2.5 rounded-full border border-red-200 text-red-500 text-xs font-bold hover:bg-red-50 transition-all disabled:opacity-50 cursor-pointer flex items-center justify-center space-x-1">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                  <span>Reject</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Reject Modal */}
      {rejectModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-end justify-center p-4">
          <div className="bg-white rounded-3xl p-6 w-full max-w-[400px] space-y-4 shadow-2xl animate-slide-up">
            <h3 className="text-base font-black text-[#111827]">Reject Payment</h3>
            <p className="text-xs text-[#9CA3AF]">
              Rejecting <strong>{rejectModal.full_name}</strong>'s Rs.{parseFloat(rejectModal.amount).toLocaleString()} payment for <strong>{rejectModal.plan_name}</strong>.
            </p>
            <div>
              <label className="block text-xs font-bold text-[#111827] mb-1 uppercase tracking-wider">Reason (required)</label>
              <textarea value={rejectReason} onChange={(e) => setRejectReason(e.target.value)}
                placeholder="e.g. Payment proof not submitted at front desk. Please visit to complete payment."
                rows={3} className="w-full px-4 py-3 rounded-2xl border border-gray-200 text-sm text-[#111827] placeholder-gray-400 focus:border-red-300 focus:ring-2 focus:ring-red-100 outline-none resize-none" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <button onClick={() => setRejectModal(null)} className="py-3 rounded-full border border-gray-200 text-xs font-bold text-[#9CA3AF] hover:text-[#111827] cursor-pointer">Cancel</button>
              <button onClick={handleReject} disabled={!rejectReason.trim() || processing}
                className="py-3 rounded-full bg-red-500 text-white text-xs font-bold hover:bg-red-600 disabled:opacity-50 cursor-pointer">
                Confirm Reject
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Reports Tab ───────────────────────────────────────────────────────────────
function ReportsTab() {
  const [downloading, setDownloading] = useState(null);
  const [toast, setToast] = useState("");

  const download = async (type, format) => {
    const key = `${type}-${format}`;
    setDownloading(key);
    try {
      const now = new Date();
      const blob = await (type === "attendance"
        ? reportsApi.downloadAttendance(format, {
            start_date: `${now.getFullYear()}-01-01`,
            end_date: now.toISOString().split("T")[0],
          })
        : reportsApi.downloadRevenue(format, {
            month: `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`,
          })
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `s2t-${type}-${now.toISOString().split("T")[0]}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
      setToast(`Downloaded ${type} report as ${format.toUpperCase()}`);
    } catch (e) {
      setToast(e.message || "Download failed");
    } finally {
      setDownloading(null);
      setTimeout(() => setToast(""), 3000);
    }
  };

  return (
    <div className="space-y-5">
      {toast && <div className="bg-[#4ADE80]/10 border border-[#4ADE80]/30 rounded-xl p-3 text-xs font-bold text-[#111827]">{toast}</div>}

      {[
        { type: "attendance", label: "Attendance Report", sub: "All member check-ins (YTD)", icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" },
        { type: "revenue", label: "Revenue Report", sub: "Monthly revenue ledger", icon: "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" },
      ].map(({ type, label, sub, icon }) => (
        <div key={type} className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm space-y-3">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-[#111827]/5 flex items-center justify-center">
              <svg className="w-5 h-5 text-[#111827]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={icon} />
              </svg>
            </div>
            <div>
              <p className="text-sm font-bold text-[#111827]">{label}</p>
              <p className="text-[10px] text-[#9CA3AF]">{sub}</p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {["csv", "excel"].map((fmt) => (
              <button key={fmt} onClick={() => download(type, fmt)}
                disabled={!!downloading}
                className="py-2.5 rounded-full border border-gray-200 text-xs font-bold text-[#111827] hover:border-[#4ADE80] hover:text-[#4ADE80] transition-all disabled:opacity-50 cursor-pointer flex items-center justify-center space-x-1.5">
                {downloading === `${type}-${fmt}` ? (
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                ) : (
                  <>
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    <span>{fmt.toUpperCase()}</span>
                  </>
                )}
              </button>
            ))}
          </div>
        </div>
      ))}

      {/* QR Generator */}
      <QRGenerator />
    </div>
  );
}

// ── Main Admin Dashboard ──────────────────────────────────────────────────────
export default function AdminDashboard() {
  const navigate = useNavigate();
  const { user, logout, refreshToken } = useAuth();
  const [activeTab, setActiveTab] = useState("overview");

  const handleLogout = async () => {
    try {
      const { auth: authApi } = await import("../../api");
      await authApi.logout(refreshToken);
    } catch (_) {}
    logout();
    navigate("/", { replace: true });
  };

  return (
    <div className="flex items-start justify-center min-h-screen bg-gray-100 sm:py-8 sm:px-4">
      <div className="w-full max-w-[440px] bg-white min-h-screen sm:min-h-0 sm:rounded-3xl sm:border border-gray-100 shadow-xl flex flex-col overflow-hidden">

        {/* Top Header */}
        <div className="bg-[#111827] px-5 py-5 flex items-center justify-between">
          <div>
            <p className="text-[10px] text-[#4ADE80] font-bold uppercase tracking-widest">Admin Panel</p>
            <h1 className="text-lg font-black text-white mt-0.5">S2T Fitness Studio</h1>
          </div>
          <button onClick={handleLogout}
            className="flex items-center space-x-1.5 text-xs text-gray-400 hover:text-[#4ADE80] font-bold transition-colors cursor-pointer bg-white/10 px-3 py-2 rounded-full">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            <span>Logout</span>
          </button>
        </div>

        {/* Tab Bar */}
        <div className="bg-[#111827] px-4 pb-4 flex space-x-1">
          {TABS.map((tab) => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)}
              className={`flex-1 flex flex-col items-center py-2.5 rounded-xl transition-all cursor-pointer ${
                activeTab === tab.key ? "bg-[#4ADE80] text-[#111827]" : "text-gray-400 hover:text-white"
              }`}>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={tab.icon} />
              </svg>
              <span className="text-[9px] font-bold mt-0.5 uppercase tracking-wide">{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto p-5">
          {activeTab === "overview" && <OverviewTab />}
          {activeTab === "members" && <MembersTab />}
          {activeTab === "payments" && <PaymentsTab />}
          {activeTab === "reports" && <ReportsTab />}
        </div>
      </div>
    </div>
  );
}
