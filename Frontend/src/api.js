import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",

  // By default axios throws an error on 404, 409, 422 and so on. We turn that
  // off so every response comes back normally and each page can just check the
  // status itself.
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

// Every call goes through here and returns { status, data }.
export async function apiCall(method, path, body) {
  const headers = {};

  // Our API reads a header called "token", not "Authorization".
  const token = getToken();
  if (token) {
    headers.token = token;
  }

  const response = await api.request({
    method: method,
    url: path,
    data: body,
    headers: headers,
  });

  return { status: response.status, data: response.data };
}

// Every error from the API looks like:
//   {"error": {"status": 422, "message": "...", "fields": {"email": "..."}}}
export function errorMessage(res) {
  const error = res.data && res.data.error;
  if (!error) return "Something went wrong.";

  const fieldMessage = Object.values(error.fields || {})[0];
  return fieldMessage || error.message;
}
