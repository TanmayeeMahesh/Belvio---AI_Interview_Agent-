import axios from 'axios'

const API = axios.create({ baseURL: 'http://localhost:8000' })

export function setAuthToken(token) {
  API.defaults.headers.common['authorization'] = token ? `Bearer ${token}` : ''
}

export default API
