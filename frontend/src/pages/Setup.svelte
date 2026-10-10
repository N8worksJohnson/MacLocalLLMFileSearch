<script>
  import { onMount, onDestroy } from 'svelte';
  import { currentPage, settings, systemInfo, downloadProgress } from '../lib/stores.js';
  import { getAvailableModels, downloadModel, getDownloadStatus, selectModel, updateSettings } from '../lib/api.js';

  let step = $state(1); // 1=welcome, 2=models, 3=downloading, 4=done
  let models = $state({ embedding: [], chat: [] });
  let selectedEmbedding = $state(null);
  let selectedChat = $state(null);
  let downloadingIds = $state(new Set());
  let downloadStatuses = $state({});
  let pollInterval = $state(null);
  let error = $state('');

  const recommended = $derived(
    $systemInfo ? $systemInfo.recommended_profile : 'standard'
  );

  onMount(async () => {
    try {
      models = await getAvailableModels();

      // Pre-select the recommended embedding model
      if (models.embedding?.length) {
        selectedEmbedding = models.embedding[0];
      }

      // Pre-select the recommended chat model
      if (models.chat?.length) {
        selectedChat = models.chat.find(m => m.profile === recommended) || models.chat[0];
      }
    } catch (e) {
      error = e.message;
    }
  });

  onDestroy(() => {
    if (pollInterval) clearInterval(pollInterval);
  });

  function formatSize(bytes) {
    if (bytes >= 1e9) return (bytes / 1e9).toFixed(1) + ' GB';
    if (bytes >= 1e6) return (bytes / 1e6).toFixed(0) + ' MB';
    return (bytes / 1e3).toFixed(0) + ' KB';
  }

  function formatSpeed(bps) {
    if (bps >= 1e6) return (bps / 1e6).toFixed(1) + ' MB/s';
    if (bps >= 1e3) return (bps / 1e3).toFixed(0) + ' KB/s';
    return bps.toFixed(0) + ' B/s';
  }

  async function startDownloads() {
    step = 3;
    error = '';
    const ids = new Set();

    try {
      if (selectedEmbedding && !selectedEmbedding.downloaded) {
        await downloadModel(selectedEmbedding.id, 'embedding');
        ids.add(selectedEmbedding.id);
      }
      if (selectedChat && !selectedChat.downloaded) {
        await downloadModel(selectedChat.id, 'chat');
        ids.add(selectedChat.id);
      }

      downloadingIds = ids; // single reactive assignment

      // If both are already downloaded, skip to done
      if (downloadingIds.size === 0) {
        await finishSetup();
        return;
      }

      // Poll for download progress
      pollInterval = setInterval(async () => {
        try {
          downloadStatuses = await getDownloadStatus();

          // Check if all downloads are complete
          let allDone = true;
          for (const id of downloadingIds) {
            const status = downloadStatuses[id];
            if (!status || status.status === 'downloading' || status.status === 'verifying') {
              allDone = false;
            }
            if (status?.status === 'failed') {
              error = status.error || 'Download failed';
              clearInterval(pollInterval);
              return;
            }
          }

          if (allDone) {
            clearInterval(pollInterval);
            await finishSetup();
          }
        } catch (e) {
          error = e.message;
        }
      }, 500);
    } catch (e) {
      error = e.message;
    }
  }

  async function finishSetup() {
    try {
      // Select the models
      if (selectedEmbedding) {
        await selectModel('embedding', selectedEmbedding.filename);
      }
      if (selectedChat) {
        await selectModel('chat', selectedChat.filename);
      }

      // Mark setup as complete
      await updateSettings({ setup_complete: true });
      settings.update(s => ({ ...s, setup_complete: true }));

      step = 4;
    } catch (e) {
      error = e.message;
    }
  }
</script>

<div class="setup">
  {#if step === 1}
    <!-- Welcome -->
    <div class="setup-card">
      <h1>Welcome to LLM File Search</h1>
      <p class="subtitle">
        Find any file by describing what's in it. LLM File Search uses AI
        to understand your files and lets you search them using natural language.
      </p>

      <div class="info-box">
        <h3>How it works</h3>
        <ol>
          <li>Download a small AI model to run locally on your machine</li>
          <li>Choose folders to scan — the AI reads and understands each file</li>
          <li>Search by describing what you're looking for in plain English</li>
        </ol>
        <p class="privacy-note">
          Everything runs locally. Your files never leave your computer.
        </p>
      </div>

      {#if $systemInfo}
        <div class="hw-info">
          <span>Detected: {$systemInfo.total_ram_gb}GB RAM</span>
          {#if $systemInfo.has_metal}<span class="chip">Apple Silicon GPU</span>{/if}
          {#if $systemInfo.has_cuda}<span class="chip">NVIDIA GPU</span>{/if}
          <span>Recommended profile: <strong>{recommended}</strong></span>
        </div>
      {/if}

      <button class="btn-primary" onclick={() => step = 2}>Get Started</button>
    </div>

  {:else if step === 2}
    <!-- Model Selection -->
    <div class="setup-card">
      <h2>Choose AI Models</h2>
      <p class="subtitle">Select models based on your hardware. You can change these later in Settings.</p>

      {#if error}
        <div class="error">{error}</div>
      {/if}

      <div class="model-section">
        <h3>Embedding Model <span class="hint">(for understanding file content)</span></h3>
        {#each models.embedding || [] as model}
          <label class="model-option" class:selected={selectedEmbedding?.id === model.id}>
            <input type="radio" name="embedding" bind:group={selectedEmbedding} value={model} />
            <div class="model-info">
              <strong>{model.name}</strong>
              <span class="model-size">{formatSize(model.size_bytes)}</span>
              <p>{model.description}</p>
              {#if model.downloaded}<span class="downloaded-badge">Downloaded</span>{/if}
            </div>
          </label>
        {/each}
      </div>

      <div class="model-section">
        <h3>Chat Model <span class="hint">(for summaries and search responses)</span></h3>
        {#each models.chat || [] as model}
          <label class="model-option" class:selected={selectedChat?.id === model.id} class:recommended={model.profile === recommended}>
            <input type="radio" name="chat" bind:group={selectedChat} value={model} />
            <div class="model-info">
              <strong>{model.name}</strong>
              {#if model.profile === recommended}<span class="rec-badge">Recommended</span>{/if}
              <span class="model-size">{formatSize(model.size_bytes)}</span>
              <p>{model.description}</p>
              <p class="model-req">Requires {model.min_ram_gb}GB+ RAM</p>
              {#if model.downloaded}<span class="downloaded-badge">Downloaded</span>{/if}
            </div>
          </label>
        {/each}
      </div>

      <div class="btn-row">
        <button class="btn-secondary" onclick={() => step = 1}>Back</button>
        <button class="btn-primary" onclick={startDownloads} disabled={!selectedEmbedding || !selectedChat}>
          Download & Continue
        </button>
      </div>
    </div>

  {:else if step === 3}
    <!-- Downloading -->
    <div class="setup-card">
      <h2>Downloading Models</h2>
      <p class="subtitle">This may take a few minutes depending on your connection speed.</p>

      {#if error}
        <div class="error">{error}</div>
      {/if}

      {#each [...downloadingIds] as modelId}
        {@const status = downloadStatuses[modelId]}
        {#if status}
          <div class="download-item">
            <div class="download-header">
              <strong>{status.filename}</strong>
              <span class="download-pct">{status.percent?.toFixed(1)}%</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" style="width: {status.percent || 0}%"></div>
            </div>
            <div class="download-footer">
              <span>{formatSize(status.downloaded_bytes)} / {formatSize(status.total_bytes)}</span>
              {#if status.speed_bps > 0}
                <span>{formatSpeed(status.speed_bps)}</span>
              {/if}
              <span class="download-status">{status.status}</span>
            </div>
          </div>
        {/if}
      {/each}
    </div>

  {:else if step === 4}
    <!-- Done -->
    <div class="setup-card">
      <h1>You're all set!</h1>
      <p class="subtitle">
        Models are loaded and ready. Now add some folders to scan,
        then start searching your files with natural language.
      </p>
      <div class="btn-row">
        <button class="btn-primary" onclick={() => { currentPage.set('settings'); }}>
          Add Folders to Scan
        </button>
        <button class="btn-secondary" onclick={() => { currentPage.set('search'); }}>
          Go to Search
        </button>
      </div>
    </div>
  {/if}
</div>

<style>
  .setup {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    padding: 2rem;
  }

  .setup-card {
    max-width: 640px;
    width: 100%;
    padding: 2.5rem;
    border-radius: 16px;
    background: #fff;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
  }

  :global(.dark) .setup-card {
    background: #16213e;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
  }

  h1 { font-size: 1.8rem; margin-bottom: 0.5rem; }
  h2 { font-size: 1.4rem; margin-bottom: 0.5rem; }
  h3 { font-size: 1rem; margin-bottom: 0.5rem; }
  .subtitle { color: #888; margin-bottom: 1.5rem; line-height: 1.5; }
  .hint { font-weight: 400; color: #888; font-size: 0.85rem; }

  .info-box {
    background: #f0f0f5;
    border-radius: 10px;
    padding: 1.2rem;
    margin-bottom: 1.5rem;
  }

  :global(.dark) .info-box { background: #1a1a3e; }

  .info-box ol { padding-left: 1.2rem; margin: 0.5rem 0; line-height: 1.8; }
  .privacy-note { margin-top: 0.8rem; font-size: 0.85rem; color: #4ade80; font-weight: 500; }

  .hw-info {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;
    font-size: 0.85rem;
    margin-bottom: 1.5rem;
    color: #888;
  }

  .chip {
    background: #6c63ff22;
    color: #6c63ff;
    padding: 0.15rem 0.5rem;
    border-radius: 6px;
    font-size: 0.8rem;
  }

  .model-section { margin-bottom: 1.5rem; }

  .model-option {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 0.8rem;
    border: 2px solid #e0e0e0;
    border-radius: 10px;
    margin-bottom: 0.5rem;
    cursor: pointer;
    transition: border-color 0.15s;
  }

  :global(.dark) .model-option { border-color: #2a2a4a; }

  .model-option.selected { border-color: #6c63ff; background: #6c63ff08; }
  .model-option.recommended { border-color: #4ade80; }
  .model-option.selected.recommended { border-color: #6c63ff; }

  .model-option input { margin-top: 0.25rem; }

  .model-info { flex: 1; }
  .model-info p { font-size: 0.85rem; color: #888; margin-top: 0.25rem; }
  .model-size { font-size: 0.8rem; color: #888; margin-left: 0.5rem; }
  .model-req { font-size: 0.8rem; color: #aaa; }

  .rec-badge {
    background: #4ade8033;
    color: #4ade80;
    padding: 0.1rem 0.4rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-left: 0.5rem;
  }

  .downloaded-badge {
    background: #6c63ff22;
    color: #6c63ff;
    padding: 0.1rem 0.4rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
  }

  .btn-row { display: flex; gap: 0.75rem; margin-top: 1rem; }

  .btn-primary {
    background: #6c63ff;
    color: white;
    border: none;
    padding: 0.7rem 1.5rem;
    border-radius: 8px;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s;
  }

  .btn-primary:hover { background: #5a52e0; }
  .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

  .btn-secondary {
    background: transparent;
    color: #6c63ff;
    border: 2px solid #6c63ff;
    padding: 0.7rem 1.5rem;
    border-radius: 8px;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
  }

  .error {
    background: #ff4444;
    color: white;
    padding: 0.5rem 0.8rem;
    border-radius: 6px;
    margin-bottom: 1rem;
    font-size: 0.9rem;
  }

  .download-item { margin-bottom: 1.5rem; }

  .download-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 0.4rem;
    font-size: 0.9rem;
  }

  .download-pct { color: #6c63ff; font-weight: 600; }

  .progress-bar {
    height: 8px;
    background: #e0e0e0;
    border-radius: 4px;
    overflow: hidden;
  }

  :global(.dark) .progress-bar { background: #2a2a4a; }

  .progress-fill {
    height: 100%;
    background: #6c63ff;
    border-radius: 4px;
    transition: width 0.3s ease;
  }

  .download-footer {
    display: flex;
    justify-content: space-between;
    margin-top: 0.3rem;
    font-size: 0.8rem;
    color: #888;
  }

  .download-status { text-transform: capitalize; }
</style>
