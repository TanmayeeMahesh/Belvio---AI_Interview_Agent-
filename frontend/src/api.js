import axios from "axios";

const API = axios.create({
  baseURL:
    import.meta.env.VITE_API_URL ||
    "http://localhost:8000"
});

export function setAuthToken(token) {
  API.defaults.headers.common["authorization"] = token;
}

export default API;