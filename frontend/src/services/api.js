async function request(path, signal) {
  const response = await fetch(path, { cache: 'no-store', signal })
  if (!response.ok) throw new Error(`Server returned ${response.status}`)
  return response.json()
}

export const api = {
  status: (signal) => request('/api/status', signal),
  photos: ({ page = 1, perPage = 18, person = 'all', burstId = null } = {}, signal) => {
    const query = new URLSearchParams({ page, per_page: perPage, person })
    if (burstId) query.set('burst_id', burstId)
    return request(`/api/photos?${query}`, signal)
  },
  bursts: ({ page = 1, perPage = 12 } = {}, signal) =>
    request(`/api/bursts?page=${page}&per_page=${perPage}`, signal),
}
