import axios from "axios";

// Where the API lives. VITE_API_URL in .env when it is set, the local default
// otherwise - the same idea as the backend reading DB_URL rather than having
// the address compiled in.
const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const api = axios.create({
  baseURL: BASE_URL,

  // By default axios throws an error on 404, 409, 422 and so on. We turn that
  // off so every response comes back normally and apiCall below can decide
  // what to do with it in one place.
  validateStatus: () => true,
});

export function getToken() {
  return localStorage.getItem("token");
}

export function saveToken(token) {
  localStorage.setItem("token", token);
}

export function removeToken() {
  localStorage.removeItem("token");
}

// A page can hand this to apiCall so that an expired token sends the user back
// to the login screen. Set once, in Layout, rather than in every page.
let onUnauthorised = null;

export function setUnauthorisedHandler(handler) {
  onUnauthorised = handler;
}

// Every call goes through here and returns { status, data, ok }.
//
// `ok` is the important part. Because validateStatus is off, `data` on a
// failed request is the error envelope, not the body a page is expecting -
// reading data.items off a 422 gives undefined, and the next .map() throws a
// blank page. Checking `ok` first is what stops that.
export async function apiCall(method, path, body) {
  const headers = {};

  // The standard Authorization header, as "Bearer <token>".
  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let response;

  try {
    response = await api.request({
      method: method,
      url: path,
      data: body,
      headers: headers,
    });
  } catch {
    // The request never reached the server at all - it is down, or the
    // browser blocked it. Shaped like every other failure so that callers
    // have one thing to check.
    return { status: 0, data: null, ok: false };
  }

  // The token expired or was tampered with. Handled here so that nine pages
  // do not each have to remember to do it - the same argument as owned_by on
  // the backend: one place instead of nine.
  if (response.status === 401) {
    removeToken();
    if (onUnauthorised) onUnauthorised();
  }

  return {
    status: response.status,
    data: response.data,
    ok: response.status >= 200 && response.status < 300,
  };
}

// Turn any query value into something safe to put in a URL. A client called
// "Smith & Co" or a search for "a#b" would otherwise cut the query string off
// at that character.
export function query(params) {
  const parts = [];

  for (const [key, value] of Object.entries(params)) {
    // Skip anything not set, so the API sees "no filter" rather than "".
    if (value === null || value === undefined || value === "") continue;
    parts.push(`${key}=${encodeURIComponent(value)}`);
  }

  return parts.length ? `?${parts.join("&")}` : "";
}

// Every error from the API looks like:
//   {"error": {"status": 422, "message": "...", "fields": {"email": "..."}}}
export function errorMessage(res) {
  if (res.status === 0) return "Could not reach the server. Is it running?";

  const error = res.data && res.data.error;
  if (!error) return "Something went wrong.";

  const fieldMessage = Object.values(error.fields || {})[0];
  return fieldMessage || error.message;
}
