<script>
  import { chatMessages, conversationId } from '../lib/stores.js';
  import { chatStream } from '../lib/api.js';
  import FileResult from './FileResult.svelte';

  let inputText = $state('');
  let isStreaming = $state(false);
  let messagesDiv = $state(null);

  function scrollToBottom() {
    if (messagesDiv) {
      requestAnimationFrame(() => {
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
      });
    }
  }

  async function sendMessage() {
    const text = inputText.trim();
    if (!text || isStreaming) return;

    inputText = '';
    isStreaming = true;

    // Add user message
    chatMessages.update(msgs => [...msgs, { role: 'user', content: text }]);
    scrollToBottom();

    // Add empty assistant message
    let assistantMsg = { role: 'assistant', content: '', results: [] };
    chatMessages.update(msgs => [...msgs, assistantMsg]);

    try {
      await chatStream(text, $conversationId, (event) => {
        if (event.type === 'results') {
          assistantMsg.results = event.data;
          chatMessages.update(msgs => {
            msgs[msgs.length - 1] = { ...assistantMsg };
            return [...msgs];
          });
          scrollToBottom();
        } else if (event.type === 'token') {
          assistantMsg.content += event.data;
          chatMessages.update(msgs => {
            msgs[msgs.length - 1] = { ...assistantMsg };
            return [...msgs];
          });
          scrollToBottom();
        } else if (event.type === 'done') {
          if (event.data?.conversation_id) {
            conversationId.set(event.data.conversation_id);
          }
        }
      });
    } catch (e) {
      assistantMsg.content = `Error: ${e.message}`;
      chatMessages.update(msgs => {
        msgs[msgs.length - 1] = { ...assistantMsg };
        return [...msgs];
      });
    } finally {
      isStreaming = false;
      scrollToBottom();
    }
  }

  function handleKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  function clearChat() {
    chatMessages.set([]);
    conversationId.set(null);
  }
</script>

<div class="chat-panel">
  <div class="messages" bind:this={messagesDiv}>
    {#if $chatMessages.length === 0}
      <div class="empty-state">
        <div class="empty-icon">🔍</div>
        <h2>Search your files</h2>
        <p>Describe what you're looking for in plain English.</p>
        <div class="examples">
          <button class="example-btn" onclick={() => { inputText = 'Find that spreadsheet with quarterly revenue numbers'; }}>
            "Find that spreadsheet with quarterly revenue numbers"
          </button>
          <button class="example-btn" onclick={() => { inputText = 'Where is the presentation about the marketing plan?'; }}>
            "Where is the presentation about the marketing plan?"
          </button>
          <button class="example-btn" onclick={() => { inputText = 'Show me photos from last summer'; }}>
            "Show me photos from last summer"
          </button>
        </div>
      </div>
    {:else}
      {#each $chatMessages as msg, i}
        <div class="message" class:user={msg.role === 'user'} class:assistant={msg.role === 'assistant'}>
          {#if msg.role === 'user'}
            <div class="msg-content user-content">{msg.content}</div>
          {:else}
            <div class="msg-content assistant-content">
              {#if msg.results?.length > 0}
                <div class="results-section">
                  {#each msg.results as result}
                    <FileResult {result} />
                  {/each}
                </div>
              {/if}
              {#if msg.content}
                <div class="response-text">{msg.content}</div>
              {:else if isStreaming && i === $chatMessages.length - 1}
                <div class="typing-indicator">
                  <span></span><span></span><span></span>
                </div>
              {/if}
            </div>
          {/if}
        </div>
      {/each}
    {/if}
  </div>

  <div class="input-area">
    {#if $chatMessages.length > 0}
      <button class="clear-btn" onclick={clearChat} title="Clear conversation">
        New
      </button>
    {/if}
    <textarea
      class="chat-input"
      placeholder="Describe the file you're looking for..."
      bind:value={inputText}
      onkeydown={handleKeydown}
      disabled={isStreaming}
      rows="1"
    ></textarea>
    <button class="send-btn" onclick={sendMessage} disabled={!inputText.trim() || isStreaming}>
      &#x2191;
    </button>
  </div>
</div>

<style>
  .chat-panel {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .messages {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    scroll-behavior: smooth;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    text-align: center;
    opacity: 0.8;
  }

  .empty-icon { font-size: 3rem; margin-bottom: 1rem; }
  .empty-state h2 { margin-bottom: 0.5rem; }
  .empty-state p { color: #888; margin-bottom: 1.5rem; }

  .examples { display: flex; flex-direction: column; gap: 0.5rem; max-width: 420px; }

  .example-btn {
    background: #f0f0f5;
    border: 1px solid #e0e0e0;
    padding: 0.6rem 1rem;
    border-radius: 8px;
    font-size: 0.85rem;
    cursor: pointer;
    text-align: left;
    color: inherit;
    transition: background 0.15s;
  }

  :global(.dark) .example-btn { background: #1e2a4a; border-color: #2a2a4a; }
  .example-btn:hover { background: #e8e8f0; }
  :global(.dark) .example-btn:hover { background: #243055; }

  .message { margin-bottom: 1rem; }

  .message.user { display: flex; justify-content: flex-end; }

  .user-content {
    background: #6c63ff;
    color: white;
    padding: 0.6rem 1rem;
    border-radius: 12px 12px 2px 12px;
    max-width: 70%;
    white-space: pre-wrap;
  }

  .assistant-content {
    max-width: 90%;
  }

  .results-section { margin-bottom: 0.75rem; }

  .response-text {
    padding: 0.6rem 0;
    line-height: 1.6;
    white-space: pre-wrap;
  }

  .typing-indicator {
    display: flex;
    gap: 4px;
    padding: 0.6rem 0;
  }

  .typing-indicator span {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #6c63ff;
    animation: blink 1.4s infinite both;
  }

  .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
  .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

  @keyframes blink {
    0%, 80%, 100% { opacity: 0.3; }
    40% { opacity: 1; }
  }

  .input-area {
    display: flex;
    align-items: flex-end;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    border-top: 1px solid #e0e0e0;
    background: #fff;
  }

  :global(.dark) .input-area { background: #16213e; border-top-color: #2a2a4a; }

  .chat-input {
    flex: 1;
    padding: 0.6rem 0.8rem;
    border: 1.5px solid #ddd;
    border-radius: 10px;
    font-size: 0.95rem;
    resize: none;
    font-family: inherit;
    background: inherit;
    color: inherit;
    outline: none;
    min-height: 40px;
    max-height: 120px;
  }

  :global(.dark) .chat-input { border-color: #3a3a5a; }
  .chat-input:focus { border-color: #6c63ff; }

  .send-btn {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    border: none;
    background: #6c63ff;
    color: white;
    font-size: 1.2rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: background 0.15s;
  }

  .send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .send-btn:hover:not(:disabled) { background: #5a52e0; }

  .clear-btn {
    background: none;
    border: 1px solid #ddd;
    padding: 0.4rem 0.7rem;
    border-radius: 6px;
    font-size: 0.8rem;
    cursor: pointer;
    color: #888;
    flex-shrink: 0;
  }

  :global(.dark) .clear-btn { border-color: #3a3a5a; }
  .clear-btn:hover { background: #f0f0f5; }
  :global(.dark) .clear-btn:hover { background: #1e2a4a; }
</style>
