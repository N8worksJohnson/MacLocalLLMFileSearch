/**
 * API client for communicating with the FastAPI backend.
 */

const BASE = '';  // Same origin in production; proxied in dev

async function request(method, path, body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(`${BASE}${path}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || err.message || 'Request failed');
  }
  return res.json();
}

// ── Status ──
export const getHealth = () => request('GET', '/api/status/health');
export const getSystemInfo = () => request('GET', '/api/status/system');

// ── Search ──
export const searchFiles = (query, filters = {}) =>
  request('POST', '/api/search', { query, ...filters });

// ── Chat (streaming) ──
export function chatStream(message, conversationId, onEvent) {
  return fetch(`${BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  }).then(async (res) => {
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || err.message || 'Chat request failed');
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6));
            onEvent(event);
          } catch (e) { /* skip malformed */ }
        }
      }
    }
  });
}

export const deleteConversation = (id) => request('DELETE', `/api/chat/${id}`);

// ── Indexing ──
export const startIndexing = (directories = null, fullRescan = false) =>
  request('POST', '/api/index/start', { directories, full_rescan: fullRescan });

export const stopIndexing = () => request('POST', '/api/index/stop');
export const getIndexStatus = () => request('GET', '/api/index/status');
export const getIndexStats = () => request('GET', '/api/index/stats');

// ── Files ──
export const openFile = (filePath) =>
  request('POST', '/api/files/open', { file_path: filePath });

export const revealFile = (filePath) =>
  request('POST', '/api/files/reveal', { file_path: filePath });

// ── Settings ──
export const getSettings = () => request('GET', '/api/settings');
export const updateSettings = (updates) => request('PUT', '/api/settings', updates);

// ── Models ──
export const getAvailableModels = () => request('GET', '/api/models/available');
export const getDownloadedModels = () => request('GET', '/api/models/downloaded');
export const getCurrentModels = () => request('GET', '/api/models/current');
export const downloadModel = (modelId, modelType) =>
  request('POST', '/api/models/download', { model_id: modelId, model_type: modelType });
export const getDownloadStatus = () => request('GET', '/api/models/download/status');
export const selectModel = (modelType, filename) =>
  request('POST', '/api/models/select', { model_type: modelType, filename });

// ── WebSocket ──
export function connectProgressWs(onMessage) {
  let reconnectDelay = 1000;
  let closed = false;
  let ws;

  function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/progress`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      reconnectDelay = 1000; // reset on successful connection
    };

    ws.onmessage = (e) => {
      try { onMessage(JSON.parse(e.data)); } catch (_) {}
    };

    ws.onerror = (e) => {
      console.warn('WebSocket error:', e);
    };

    ws.onclose = () => {
      if (closed) return;
      setTimeout(() => {
        if (!closed) connect();
      }, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 2, 30000);
    };
  }

  connect();

  // Return cleanup function
  return () => {
    closed = true;
    if (ws) ws.close();
  };
}
