// Production API Service Layer for Personal Finance Intelligence Agent

const TOKEN_KEY = "pfa_token";
const USER_KEY = "pfa_user";

export const session = {
  get token() {
    return localStorage.getItem(TOKEN_KEY);
  },
  set token(val) {
    if (val) localStorage.setItem(TOKEN_KEY, val);
    else localStorage.removeItem(TOKEN_KEY);
  },
  get user() {
    try {
      const u = localStorage.getItem(USER_KEY);
      return u ? JSON.parse(u) : null;
    } catch {
      return null;
    }
  },
  set user(val) {
    if (val) localStorage.setItem(USER_KEY, JSON.stringify(val));
    else localStorage.removeItem(USER_KEY);
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }
};

export class ApiError extends Error {
  constructor(status, code, message, details) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

let unauthorizedListeners = [];
export function onUnauthorized(callback) {
  unauthorizedListeners.push(callback);
  return () => {
    unauthorizedListeners = unauthorizedListeners.filter((fn) => fn !== callback);
  };
}

export async function request(path, { method = "GET", body, form, params, auth = true } = {}) {
  // Uses relative path so Vite proxy (dev) or FastAPI mount (prod) handles the origin seamlessly
  const url = new URL("/api/v1" + path, window.location.origin);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== "") {
        url.searchParams.set(k, v);
      }
    }
  }

  const headers = {};
  if (auth && session.token) {
    headers["Authorization"] = "Bearer " + session.token;
  }

  let payload;
  if (form) {
    payload = form;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(url, { method, headers, body: payload });
  } catch (err) {
    throw new ApiError(0, "NETWORK_ERROR", "Cannot reach the server. Please check your backend connection.", err);
  }

  if (res.status === 204) return null;

  let data = null;
  try {
    data = await res.json();
  } catch {
    // Non-JSON response
  }

  if (res.ok) return data;

  const errObj = data?.error || {};
  if (res.status === 401 && auth) {
    session.clear();
    unauthorizedListeners.forEach((fn) => fn());
  }

  let message = errObj.message || `Request failed with status ${res.status}`;
  if (res.status === 422 && Array.isArray(errObj.details) && errObj.details.length) {
    message = errObj.details.map((d) => (d.field ? `${d.field}: ` : "") + d.message).join("; ");
  }

  throw new ApiError(res.status, errObj.code || "HTTP_ERROR", message, errObj.details);
}

// Grouped API helpers
export const api = {
  auth: {
    login: async (email, password) => {
      const data = await request("/auth/login", {
        method: "POST",
        body: { email, password },
        auth: false,
      });
      session.token = data.access_token;
      // Fetch profile right after login
      try {
        const profile = await request("/profile");
        session.user = profile;
      } catch {
        session.user = { email };
      }
      return data;
    },
    register: async (email, password) => {
      return request("/auth/register", {
        method: "POST",
        body: { email, password },
        auth: false,
      });
    },
    logout: async () => {
      try {
        await request("/auth/logout", { method: "POST" });
      } finally {
        session.clear();
      }
    },
    profile: () => request("/profile"),
  },

  accounts: {
    list: () => request("/accounts"),
    create: (data) => request("/accounts", { method: "POST", body: data }),
  },

  categories: {
    list: () => request("/categories"),
  },

  transactions: {
    list: (params) => request("/transactions", { params }),
    create: (data) => request("/transactions", { method: "POST", body: data }),
    importCsv: (accountId, file, signConvention = "negative_is_expense") => {
      const form = new FormData();
      form.append("account_id", accountId);
      form.append("sign_convention", signConvention);
      form.append("file", file);
      return request("/transactions/import", { method: "POST", form });
    },
    recategorize: () => request("/transactions/recategorize", { method: "POST" }),
    delete: (txId) => request(`/transactions/${txId}`, { method: "DELETE" }),
  },

  budgets: {
    list: () => request("/budgets"),
    create: (data) => request("/budgets", { method: "POST", body: data }),
    status: (month) => request("/budgets/status", { params: { month } }),
    delete: (id) => request(`/budgets/${id}`, { method: "DELETE" }),
  },

  goals: {
    list: () => request("/goals"),
    create: (data) => request("/goals", { method: "POST", body: data }),
    contribute: (goalId, amount) =>
      request(`/goals/${goalId}/contributions`, { method: "POST", body: { amount } }),
  },

  analytics: {
    summary: (startDate, endDate) =>
      request("/analytics/summary", { params: { start_date: startDate, end_date: endDate } }),
    categories: (month) => request("/analytics/categories", { params: { month } }),
    monthly: () => request("/analytics/monthly"),
    anomalies: (startDate, endDate) =>
      request("/analytics/anomalies", { params: { start_date: startDate, end_date: endDate } }),
  },

  alerts: {
    list: () => request("/alerts"),
    markAllRead: () => request("/alerts/mark-all-read", { method: "POST" }),
  },

  agent: {
    chat: (message, runId = null) =>
      request("/agent/chat", { method: "POST", body: { message, run_id: runId } }),
    messages: () => request("/agent/messages"),
  },
};
