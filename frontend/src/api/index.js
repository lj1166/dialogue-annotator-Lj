import axios from 'axios'

const api = axios.create({ baseURL: '/api', timeout: 120000 })

export const getConversations = () => api.get('/conversations')
export const getConversation = (id) => api.get(`/conversations/${id}`)
export const getStats = () => api.get('/stats')
export const getAnnotation = (conversationId, turnIndex) =>
  api.get(`/annotations/${conversationId}/${turnIndex}`)
export const saveAnnotation = (data) => api.put('/annotations', data)
export const aiSuggest = (data) => api.post('/ai/suggest', data)

export const exportJsonUrl = '/api/export/json'
export const exportCsvUrl = '/api/export/csv'

export default api
