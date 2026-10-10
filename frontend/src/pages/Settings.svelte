<script>
  import { onMount } from 'svelte';
  import { settings, scanProgress } from '../lib/stores.js';
  import {
    getSettings, updateSettings, startIndexing, stopIndexing,
    getIndexStats,
  } from '../lib/api.js';

  let directories = $state([]);
  let newDir = $state('');
  let excludeText = $state('');
  let theme = $state('dark');
  let stats = $state(null);
  let saving = $state(false);

  onMount(async () => {
    try {
      const s = await getSettings();
      settings.set(s);
      directories = s.scan_directories || [];
      excludeText = (s.exclude_patterns || []).join('\n');
      theme = s.theme || 'dark';

      stats = await getIndexStats();
    } catch (e) { /* ok */ }
  });

  async function addDirectory() {
    const dir = newDir.trim();
    if (!dir || directories.includes(dir)) return;

    directories = [...directories, dir];
    newDir = '';
    await save();
  }

  async function removeDirectory(dir) {
    directories = directories.filter(d => d !== dir);
    await save();
  }

  async function save() {
    saving = true;
    try {
      const updated = await updateSettings({
        scan_directories: directories,
        exclude_patterns: excludeText.split('\n').filter(p => p.trim()),
        theme,
      });
      settings.set(updated);
    } catch (e) {
      console.error('Failed to save settings:', e);
    } finally {
      saving = false;
    }
  }

  async function toggleTheme() {
    theme = theme === 'dark' ? 'light' : 'dark';
    await save();
  }

  async function handleStartScan() {
    await startIndexing();
  }

  async function handleStopScan() {
    await stopIndexing();
  }

  function handleKeydown(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      addDirectory();
    }
  }
</script>

<div class="settings-page">
  <div class="settings-content">
    <h1>Settings</h1>

    <!-- Scan Directories -->
    <section class="setting-section">
      <h2>Scan Directories</h2>
      <p class="section-desc">Choose which folders to scan for files.</p>

      <div class="dir-list">
        {#each directories as dir}
          <div class="dir-item">
            <span class="dir-path">{dir}</span>
            <button class="remove-btn" onclick={() => removeDirectory(dir)}>Remove</button>
          </div>
        {/each}
      </div>

      <div class="add-dir">
        <input
          type="text"
          placeholder="Enter a directory path (e.g. /Users/you/Documents)"
          bind:value={newDir}
          onkeydown={handleKeydown}
        />
        <button class="btn-small" onclick={addDirectory}>Add</button>
      </div>
    </section>

    <!-- Scanning Controls -->
    <section class="setting-section">
      <h2>Indexing</h2>
      {#if stats}
        <p class="section-desc">
          {stats.total_files_indexed} files indexed
          {#if stats.file_state_stats?.failed > 0}
            ({stats.file_state_stats.failed} failed)
          {/if}
        </p>
      {/if}

      <div class="btn-row">
        {#if $scanProgress.state === 'indexing' || $scanProgress.state === 'scanning'}
          <button class="btn-small btn-danger" onclick={handleStopScan}>Stop Scan</button>
          <span class="scan-status">
            {$scanProgress.state === 'scanning' ? 'Scanning...' : `${$scanProgress.files_processed}/${$scanProgress.files_to_process} files`}
          </span>
        {:else}
          <button class="btn-small" onclick={handleStartScan} disabled={directories.length === 0}>
            Start Scan
          </button>
          <button class="btn-small" onclick={() => startIndexing(null, true)} disabled={directories.length === 0}>
            Full Rescan
          </button>
        {/if}
      </div>
    </section>

    <!-- Exclude Patterns -->
    <section class="setting-section">
      <h2>Exclude Patterns</h2>
      <p class="section-desc">One pattern per line. Files/folders matching these will be skipped.</p>
      <textarea
        class="exclude-input"
        bind:value={excludeText}
        onblur={save}
        rows="6"
      ></textarea>
    </section>

    <!-- Theme -->
    <section class="setting-section">
      <h2>Theme</h2>
      <button class="btn-small" onclick={toggleTheme}>
        Switch to {theme === 'dark' ? 'Light' : 'Dark'} Mode
      </button>
    </section>

    <!-- About -->
    <section class="setting-section">
      <h2>About</h2>
      <p class="section-desc">
        LLM File Search v0.1.0<br>
        Powered by local AI. Your files never leave your computer.
      </p>
    </section>
  </div>
</div>

<style>
  .settings-page {
    height: 100%;
    overflow-y: auto;
    padding: 1.5rem;
  }

  .settings-content {
    max-width: 640px;
    margin: 0 auto;
  }

  h1 { margin-bottom: 1.5rem; font-size: 1.5rem; }
  h2 { margin-bottom: 0.3rem; font-size: 1rem; }

  .setting-section {
    margin-bottom: 2rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid #e0e0e0;
  }

  :global(.dark) .setting-section { border-bottom-color: #2a2a4a; }

  .section-desc { color: #888; font-size: 0.85rem; margin-bottom: 0.75rem; }

  .dir-list { margin-bottom: 0.5rem; }

  .dir-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.4rem 0.6rem;
    background: #f0f0f5;
    border-radius: 6px;
    margin-bottom: 0.3rem;
    font-size: 0.9rem;
  }

  :global(.dark) .dir-item { background: #1e2a4a; }

  .dir-path { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .remove-btn {
    background: none;
    border: none;
    color: #ff4444;
    cursor: pointer;
    font-size: 0.8rem;
    flex-shrink: 0;
  }

  .add-dir {
    display: flex;
    gap: 0.5rem;
  }

  .add-dir input {
    flex: 1;
    padding: 0.5rem 0.7rem;
    border: 1.5px solid #ddd;
    border-radius: 6px;
    font-size: 0.9rem;
    background: inherit;
    color: inherit;
  }

  :global(.dark) .add-dir input {
    border-color: #3a3a5a;
  }

  .exclude-input {
    width: 100%;
    padding: 0.5rem;
    border: 1.5px solid #ddd;
    border-radius: 6px;
    font-family: monospace;
    font-size: 0.85rem;
    resize: vertical;
    background: inherit;
    color: inherit;
  }

  :global(.dark) .exclude-input { border-color: #3a3a5a; }

  .btn-row { display: flex; gap: 0.5rem; align-items: center; }

  .btn-small {
    background: #6c63ff;
    color: white;
    border: none;
    padding: 0.4rem 0.8rem;
    border-radius: 6px;
    font-size: 0.85rem;
    cursor: pointer;
    transition: background 0.15s;
  }

  .btn-small:hover { background: #5a52e0; }
  .btn-small:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-small.btn-danger { background: #ff4444; }
  .btn-small.btn-danger:hover { background: #cc3333; }

  .scan-status { font-size: 0.85rem; color: #888; }

  .error-text {
    color: #ff4444;
    font-size: 0.85rem;
    margin-top: 0.3rem;
  }
</style>
