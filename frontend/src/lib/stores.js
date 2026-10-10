/**
 * Svelte stores for application state.
 */
import { writable } from 'svelte/store';

// Current page: 'setup' | 'search' | 'settings'
export const currentPage = writable('search');

// Chat state
export const chatMessages = writable([]);
export const conversationId = writable(null);

// Scan progress from WebSocket
export const scanProgress = writable({
  state: 'idle',
  files_discovered: 0,
  files_to_process: 0,
  files_processed: 0,
  files_failed: 0,
  current_file: '',
  elapsed_seconds: 0,
});

// App settings
export const settings = writable({
  scan_directories: [],
  exclude_patterns: [],
  theme: 'dark',
  setup_complete: false,
});

// Model download progress
export const downloadProgress = writable({});

// System info
export const systemInfo = writable(null);
