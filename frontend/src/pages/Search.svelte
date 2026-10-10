<script>
  import ChatPanel from '../components/ChatPanel.svelte';
  import { scanProgress } from '../lib/stores.js';
  import { getIndexStats } from '../lib/api.js';
  import { onMount } from 'svelte';

  let stats = $state(null);

  onMount(async () => {
    try {
      stats = await getIndexStats();
    } catch (e) { /* Ignore if no index yet */ }
  });
</script>

<div class="search-page">
  {#if $scanProgress.state === 'indexing' || $scanProgress.state === 'scanning'}
    <div class="scan-bar">
      <div class="scan-bar-text">
        {$scanProgress.state === 'scanning' ? 'Scanning directories...' : `Indexing: ${$scanProgress.files_processed} / ${$scanProgress.files_to_process} files`}
      </div>
      <div class="scan-bar-progress">
        <div
          class="scan-bar-fill"
          style="width: {$scanProgress.files_to_process > 0 ? ($scanProgress.files_processed / $scanProgress.files_to_process * 100) : 0}%"
        ></div>
      </div>
    </div>
  {/if}

  <ChatPanel />
</div>

<style>
  .search-page {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .scan-bar {
    padding: 0.4rem 1rem;
    background: #6c63ff15;
    border-bottom: 1px solid #6c63ff30;
    font-size: 0.82rem;
  }

  .scan-bar-text { margin-bottom: 0.25rem; color: #6c63ff; }

  .scan-bar-progress {
    height: 3px;
    background: #e0e0e0;
    border-radius: 2px;
  }

  :global(.dark) .scan-bar-progress { background: #2a2a4a; }

  .scan-bar-fill {
    height: 100%;
    background: #6c63ff;
    border-radius: 2px;
    transition: width 0.3s ease;
  }
</style>
