<script>
  import { openFile, revealFile } from '../lib/api.js';

  let { result } = $props();

  const icons = {
    document: '\ud83d\udcc4',
    spreadsheet: '\ud83d\udcca',
    presentation: '\ud83d\udcfd\ufe0f',
    code: '\ud83d\udcbb',
    image: '\ud83d\uddbc\ufe0f',
    video: '\ud83c\udfac',
    audio: '\ud83c\udfb5',
    text: '\ud83d\udcdd',
    archive: '\ud83d\udce6',
    email: '\ud83d\udce7',
    other: '\ud83d\udcc1',
  };

  const fileType = result.metadata?.file_type || 'other';
  const icon = icons[fileType] || icons.other;

  function formatDate(ts) {
    if (!ts) return '';
    return new Date(ts * 1000).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  }

  function formatSize(bytes) {
    if (!bytes) return '';
    if (bytes >= 1e6) return (bytes / 1e6).toFixed(1) + ' MB';
    if (bytes >= 1e3) return (bytes / 1e3).toFixed(0) + ' KB';
    return bytes + ' B';
  }

  function shortenPath(path) {
    const parts = path.split('/');
    if (parts.length <= 4) return path;
    return parts.slice(0, 2).join('/') + '/.../' + parts.slice(-2).join('/');
  }
</script>

<div class="file-result">
  <div class="result-icon">{icon}</div>
  <div class="result-body">
    <div class="result-header">
      <span class="result-name">{result.file_name}</span>
      <span class="result-score" title="Relevance score">{(result.score * 100).toFixed(0)}%</span>
    </div>
    <div class="result-path" title={result.file_path}>{shortenPath(result.file_path)}</div>
    {#if result.summary}
      <div class="result-summary">{result.summary}</div>
    {/if}
    <div class="result-meta">
      <span class="meta-type">{fileType}</span>
      {#if result.metadata?.file_size}
        <span>{formatSize(result.metadata.file_size)}</span>
      {/if}
      {#if result.metadata?.modified_at}
        <span>{formatDate(result.metadata.modified_at)}</span>
      {/if}
    </div>
    <div class="result-actions">
      <button class="action-btn" onclick={() => openFile(result.file_path)}>Open</button>
      <button class="action-btn" onclick={() => revealFile(result.file_path)}>Reveal</button>
    </div>
  </div>
</div>

<style>
  .file-result {
    display: flex;
    gap: 0.75rem;
    padding: 0.8rem;
    border-radius: 10px;
    background: #f8f8fa;
    margin-bottom: 0.5rem;
    transition: background 0.15s;
  }

  :global(.dark) .file-result { background: #1e2a4a; }

  .file-result:hover { background: #f0f0f5; }
  :global(.dark) .file-result:hover { background: #243055; }

  .result-icon { font-size: 1.8rem; flex-shrink: 0; }

  .result-body { flex: 1; min-width: 0; }

  .result-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
  }

  .result-name { font-weight: 600; font-size: 0.95rem; }

  .result-score {
    font-size: 0.8rem;
    color: #6c63ff;
    font-weight: 600;
    flex-shrink: 0;
    margin-left: 0.5rem;
  }

  .result-path {
    font-size: 0.78rem;
    color: #888;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    margin-top: 0.15rem;
  }

  .result-summary {
    font-size: 0.85rem;
    color: #666;
    margin-top: 0.3rem;
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  :global(.dark) .result-summary { color: #aaa; }

  .result-meta {
    display: flex;
    gap: 0.75rem;
    margin-top: 0.35rem;
    font-size: 0.78rem;
    color: #999;
  }

  .meta-type {
    background: #6c63ff15;
    color: #6c63ff;
    padding: 0.05rem 0.35rem;
    border-radius: 4px;
    font-weight: 500;
  }

  .result-actions {
    display: flex;
    gap: 0.4rem;
    margin-top: 0.35rem;
  }

  .action-btn {
    background: none;
    border: 1px solid #ddd;
    padding: 0.2rem 0.6rem;
    border-radius: 5px;
    font-size: 0.78rem;
    cursor: pointer;
    color: inherit;
    transition: all 0.15s;
  }

  :global(.dark) .action-btn { border-color: #3a3a5a; }

  .action-btn:hover {
    background: #6c63ff;
    color: white;
    border-color: #6c63ff;
  }
</style>
