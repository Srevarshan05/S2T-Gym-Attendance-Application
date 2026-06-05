/**
 * api.js — Centralized API service for S2T Fitness Studio
 * All HTTP calls to FastAPI backend go through this module.
 * Base URL: http://localhost:8000/api/v1
 */

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

// ── Token store (module-level, in-memory only — never localStorage) ──────────
let _accessToken = null;
let _refreshToken = null;
let _onTokenRefreshed = null; // callback to update AuthContext

export function setTokens(access, refresh) {
  _accessToken = access;
  _refreshToken = refresh;
}

export function clearTokens() {
  _accessToken = null;
  _refreshToken = null;
}

export function getAccessToken() {
  return _accessToken;
}

export function setTokenRefreshCallback(cb) {
  _onTokenRefreshed = cb;
}

// ── Core fetch wrapper ────────────────────────────────────────────────────────
async function request(path, options = {}, retry = true) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (_accessToken) {
    headers["Authorization"] = `Bearer ${_accessToken}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  // Auto-refresh on 401
  if (res.status === 401 && retry && _refreshToken) {
    try {
      const refreshRes = await fetch(`${BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: _refreshToken }),
      });
      if (refreshRes.ok) {
        const data = await refreshRes.json();
        setTokens(data.access_token, data.refresh_token);
        if (_onTokenRefreshed) _onTokenRefreshed(data);
        return request(path, options, false); // retry once
      }
    } catch (_) {
      // refresh failed — let original 401 propagate
    }
  }

  if (!res.ok) {
    let errorMsg = `Server error (${res.status})`;
    try {
      const errData = await res.json();
      if (Array.isArray(errData.detail)) {
        // FastAPI 422 validation errors: [{loc: ["body","field"], msg: "...", type: "..."}]
        errorMsg = errData.detail
          .map((e) => {
            const field = e.loc && e.loc.length > 1
              ? String(e.loc[e.loc.length - 1]).replace(/_/g, " ")
              : null;
            return field ? `${field}: ${e.msg}` : e.msg;
          })
          .join(" | ");
      } else if (typeof errData.detail === "string") {
        errorMsg = errData.detail;
      } else if (typeof errData.message === "string") {
        errorMsg = errData.message;
      }
    } catch (_) {}
    throw new Error(errorMsg);
  }

  // 204 No Content
  if (res.status === 204) return null;
  return res.json();
}

// ── Auth ─────────────────────────────────────────────────────────────────────
export const auth = {
  login: (memberId, password) =>
    request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ member_id: memberId, password }),
    }),

  register: (payload) =>
    request("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  logout: (refreshToken) =>
    request("/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    }),

  refresh: (refreshToken) =>
    request("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    }),
};

// ── Plans (public — no auth) ──────────────────────────────────────────────────
export const plans = {
  list: () => request("/plans"),
};

// ── Dashboard (admin) ─────────────────────────────────────────────────────────
export const dashboard = {
  getOverview: () => request("/dashboard/overview"),
};

// ── Members (admin) ───────────────────────────────────────────────────────────
export const members = {
  list: (page = 1, perPage = 20, search = "") =>
    request(`/members?page=${page}&per_page=${perPage}${search ? `&q=${encodeURIComponent(search)}` : ""}`),

  get: (memberId) => request(`/members/${memberId}`),

  update: (memberId, payload) =>
    request(`/members/${memberId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  deactivate: (memberId) =>
    request(`/members/${memberId}`, { method: "DELETE" }),
};

// ── Payments ──────────────────────────────────────────────────────────────────
export const payments = {
  getPending: () => request("/payments/pending"),

  submit: (planId) =>
    request("/payments/submit", {
      method: "POST",
      body: JSON.stringify({ plan_id: planId }),
    }),

  approve: (paymentId, customEndDate = null) =>
    request(`/payments/${paymentId}/approve`, {
      method: "POST",
      body: JSON.stringify({ custom_end_date: customEndDate }),
    }),

  reject: (paymentId, reason) =>
    request(`/payments/${paymentId}/reject`, {
      method: "POST",
      body: JSON.stringify({ rejection_reason: reason }),
    }),
};

// ── Attendance ─────────────────────────────────────────────────────────────────
export const attendance = {
  checkin: (session) =>
    request("/attendance/checkin", {
      method: "POST",
      body: JSON.stringify({ session }),
    }),

  getCalendar: (year, month) =>
    request(`/attendance/calendar?year=${year}&month=${month}`),
};

// ── Reports (admin — returns blob) ────────────────────────────────────────────
export const reports = {
  downloadAttendance: async (format = "csv", params = {}) => {
    const qs = new URLSearchParams({ format, ...params }).toString();
    const res = await fetch(`${BASE_URL}/reports/attendance?${qs}`, {
      headers: { Authorization: `Bearer ${_accessToken}` },
    });
    if (!res.ok) throw new Error("Download failed");
    return res.blob();
  },

  downloadRevenue: async (format = "csv", params = {}) => {
    const qs = new URLSearchParams({ format, ...params }).toString();
    const res = await fetch(`${BASE_URL}/reports/revenue?${qs}`, {
      headers: { Authorization: `Bearer ${_accessToken}` },
    });
    if (!res.ok) throw new Error("Download failed");
    return res.blob();
  },
};
