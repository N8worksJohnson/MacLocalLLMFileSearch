<script>
  import { onMount, onDestroy } from 'svelte';
  import { currentPage, settings, scanProgress, systemInfo } from './lib/stores.js';
  import { getSettings, getSystemInfo, connectProgressWs } from './lib/api.js';
  import SearchPage from './pages/Search.svelte';
  import SettingsPage from './pages/Settings.svelte';
  import SetupPage from './pages/Setup.svelte';

  let loading = $state(true);
  let wsCleanup;

  onMount(async () => {
    try {
      // Fetch independently so one failure doesn't block the others
      const [settingsResult, sysResult] = await Promise.allSettled([
        getSettings(),
        getSystemInfo(),
      ]);

      if (settingsResult.status === 'fulfilled') {
        settings.set(settingsResult.value);
        if (!settingsResult.value.setup_complete) {
          currentPage.set('setup');
        }
      } else {
        console.error('Failed to load settings:', settingsResult.reason);
      }

      if (sysResult.status === 'fulfilled') {
        systemInfo.set(sysResult.value);
      } else {
        console.error('Failed to load system info:', sysResult.reason);
      }

      // Connect WebSocket for scan progress
      wsCleanup = connectProgressWs((data) => {
        scanProgress.set(data);
      });
    } catch (e) {
      console.error('Failed to initialize:', e);
    } finally {
      loading = false;
    }
  });

  onDestroy(() => {
    if (wsCleanup) wsCleanup();
  });
</script>

{#if loading}
  <div class="loading">
    <div class="spinner"></div>
    <p>Starting LLM File Search...</p>
  </div>
{:else}
  <div class="app" class:dark={$settings.theme === 'dark'}>
    <!-- Navigation bar -->
    <nav class="nav">
      <div class="nav-brand">LLM File Search</div>
      <div class="nav-links">
        <button
          class="nav-btn"
          class:active={$currentPage === 'search'}
          onclick={() => currentPage.set('search')}
        >
          Search
        </button>
        <button
          class="nav-btn"
          class:active={$currentPage === 'settings'}
          onclick={() => currentPage.set('settings')}
        >
          Settings
        </button>
      </div>
      <div class="nav-status">
        {#if $scanProgress.state === 'indexing' || $scanProgress.state === 'scanning'}
          <span class="status-dot pulse"></span>
          <span class="status-text">
            {$scanProgress.state === 'scanning' ? 'Scanning...' : `Indexing ${$scanProgress.files_processed}/${$scanProgress.files_to_process}`}
          </span>
        {/if}
      </div>
    </nav>

    <!-- Page content -->
    <main class="content">
      {#if $currentPage === 'setup'}
        <SetupPage />
      {:else if $currentPage === 'search'}
        <SearchPage />
      {:else if $currentPage === 'settings'}
        <SettingsPage />
      {/if}
    </main>
  </div>
{/if}

<style>
  :global(body) {
    margin: 0;
    padding: 0;
  }

  .loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    background: #1a1a2e;
    color: #e0e0e0;
    font-size: 1.1rem;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 3px solid #333;
    border-top-color: #6c63ff;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-bottom: 1rem;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  .app {
    display: flex;
    flex-direction: column;
    height: 100vh;
    background: #f5f5f7;
    color: #1d1d1f;
  }

  .app.dark {
    background: #1a1a2e;
    color: #e0e0e0;
  }

  .nav {
    display: flex;
    align-items: center;
    padding: 0 1rem;
    height: 48px;
    background: #fff;
    border-bottom: 1px solid #e0e0e0;
    user-select: none;
    -webkit-app-region: drag;
  }

  .dark .nav {
    background: #16213e;
    border-bottom-color: #2a2a4a;
  }

  .nav-brand {
    font-weight: 700;
    font-size: 0.95rem;
    margin-right: 2rem;
    color: #6c63ff;
  }

  .nav-links {
    display: flex;
    gap: 0.25rem;
    -webkit-app-region: no-drag;
  }

  .nav-btn {
    background: none;
    border: none;
    padding: 0.4rem 0.8rem;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.85rem;
    color: inherit;
    transition: background 0.15s;
  }

  .nav-btn:hover { background: rgba(108, 99, 255, 0.1); }
  .nav-btn.active { background: rgba(108, 99, 255, 0.15); color: #6c63ff; font-weight: 600; }

  .nav-status {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.8rem;
    -webkit-app-region: no-drag;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    background: #4ade80;
    border-radius: 50%;
  }

  .status-dot.pulse {
    animation: pulse 1.5s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  .status-text { color: #888; }
  .dark .status-text { color: #aaa; }

  .content {
    flex: 1;
    overflow: hidden;
  }
</style>
