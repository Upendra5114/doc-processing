<script>
  import { onMount } from "svelte";

  // 1. Wrap all your reactive variables in $state()
  let ws = $state(null);
  let wsUrl = $state("");
  let connected = $state(false);
  let connecting = $state(false);

  let selectedFile = $state(null);
  let dbPath = $state("data.db");

  let statusText = $state("Idle");
  let steps = $state([
    { index: 0, label: "Upload decode", status: "pending", detail: "" },
    { index: 1, label: "Pre-check", status: "pending", detail: "" },
    { index: 2, label: "OCR / Parse", status: "pending", detail: "" },
    { index: 3, label: "Transform", status: "pending", detail: "" },
    { index: 4, label: "Store", status: "pending", detail: "" },
    { index: 5, label: "Finalize", status: "pending", detail: "" }
  ]);
  
  let logs = $state([]);
  let resultData = $state(null);
  let errorText = $state("");

  function getDefaultWsUrl() {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    return `${proto}://${window.location.hostname}:8000/ws/process`;
  }

  function resetRunState() {
    statusText = "Idle";
    errorText = "";
    resultData = null;
    logs = [];
    steps = steps.map((s) => ({ ...s, status: "pending", detail: "" }));
  }

  onMount(() => {
    wsUrl = getDefaultWsUrl();
  });

  function normalizeWsUrl(raw) {
    const value = (raw || "").trim();
    if (!value) return getDefaultWsUrl();

    try {
      const u = new URL(value);
      if (u.pathname === "/ws") u.pathname = "/ws/process";
      return u.toString();
    } catch {
      return getDefaultWsUrl();
    }
  }

  function connectWs() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;
    connecting = true;
    errorText = "";

    const targetUrl = normalizeWsUrl(wsUrl);
    wsUrl = targetUrl;

    logs = [...logs, `[ws] connecting to ${targetUrl}`];
    const socket = new WebSocket(targetUrl);
    ws = socket;

    socket.onopen = () => {
      if (ws !== socket) return;
      connected = true;
      connecting = false;
      statusText = "Connected";
      logs = [...logs, `[ws] connected to ${targetUrl}`];
    };

    socket.onmessage = (event) => {
      if (ws !== socket) return;
      try {
        const msg = JSON.parse(event.data);

        if (msg.event === "ping") {
          socket.send(JSON.stringify({ action: "pong", ts: Date.now() }));
          return;
        }

        if (msg.event === "connected") {
          logs = [...logs, `[server] frontend connected: ${msg.client ?? "unknown"}`];
          return;
        }

        if (msg.event === "log") {
          logs = [...logs, msg.message];
          return;
        }

        if (msg.event === "step") {
          steps = steps.map((s) =>
            s.index === msg.index
              ? { ...s, status: msg.status || s.status, detail: msg.detail || "" }
              : s
          );
          statusText = `Step ${msg.index}: ${msg.status}`;
          return;
        }

        if (msg.event === "result") {
          resultData = msg.data;
          statusText = "Completed";
          return;
        }

        if (msg.event === "error") {
          errorText = msg.detail || "Unknown server error";
          statusText = "Error";
          logs = [...logs, `[error] ${errorText}`];
          return;
        }

        if (msg.event === "done") {
          statusText = msg.ok ? "Done" : "Done with errors";
          return;
        }
      } catch {
        logs = [...logs, `[raw] ${event.data}`];
      }
    };

    socket.onerror = (ev) => {
      if (ws !== socket) return;
      errorText = "WebSocket error";
      statusText = "Error";
      logs = [...logs, `[ws] error ${JSON.stringify(ev)}`];
    };

    socket.onclose = (event) => {
      if (ws !== socket) return;
      connected = false;
      connecting = false;
      statusText = "Disconnected";
      logs = [...logs, `[ws] disconnected code=${event.code} reason=${event.reason || "(none)"}`];
      ws = null;
    };
  }

  function disconnectWs() {
    if (!ws) return;
    const socket = ws;
    ws = null;
    connected = false;
    connecting = false;
    socket.close(1000, "client disconnect");
  }

  function onFileChange(event) {
    const file = event.target.files?.[0];
    selectedFile = file || null;
  }

  function fileToBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const dataUrl = reader.result;
        const base64 = String(dataUrl).split(",")[1] || "";
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  async function sendProcess() {
    errorText = "";
    resultData = null;

    if (!connected || !ws || ws.readyState !== WebSocket.OPEN) {
      errorText = "WebSocket is not connected";
      return;
    }

    if (!selectedFile) {
      errorText = "Please select a file";
      return;
    }

    const allowed = [".pdf", ".jpg", ".jpeg", ".png"];
    const lower = selectedFile.name.toLowerCase();
    const ok = allowed.some((ext) => lower.endsWith(ext));
    if (!ok) {
      errorText = "Only .pdf, .jpg, .jpeg, .png are supported";
      return;
    }

    resetRunState();
    statusText = "Encoding file...";

    try {
      const file_b64 = await fileToBase64(selectedFile);

      const payload = {
        action: "process",
        filename: selectedFile.name,
        db_path: dbPath || "data.db",
        file_b64
      };

      ws.send(JSON.stringify(payload));
      statusText = "Processing started";
      logs = [...logs, `[send] ${selectedFile.name}`];
    } catch (e) {
      errorText = `Failed to encode file: ${e?.message || e}`;
      statusText = "Error";
    }
  }
</script>

<main class="page">
  <section class="card">
    <h1>Doc Processing (WebSocket)</h1>
    <p class="muted">Pure WebSocket client for <code>/ws/process</code></p>

    <div class="row">
      <label for="wsUrl">WebSocket URL</label>
      <input id="wsUrl" class="input" bind:value={wsUrl} placeholder="ws://localhost:8000/ws/process" />
    </div>

    <div class="actions">
      <button class="btn" on:click={connectWs} disabled={connected || connecting}>
        {connecting ? "Connecting..." : "Connect"}
      </button>
      <button class="btn btn-secondary" on:click={disconnectWs} disabled={!connected}>
        Disconnect
      </button>
      <span class:ok={connected} class:bad={!connected} class="status-dot">
        {connected ? "Connected" : "Disconnected"}
      </span>
    </div>
  </section>

  <section class="card">
    <h2>Process Document</h2>

    <div class="row">
      <label for="file">File</label>
      <input id="file" class="input" type="file" accept=".pdf,.jpg,.jpeg,.png" on:change={onFileChange} />
    </div>

    <div class="row">
      <label for="dbPath">DB Path</label>
      <input id="dbPath" class="input" bind:value={dbPath} />
    </div>

    <div class="actions">
      <button class="btn" on:click={sendProcess} disabled={!connected}>
        Start Processing
      </button>
      <span class="status-text">{statusText}</span>
    </div>

    {#if errorText}
      <p class="error">{errorText}</p>
    {/if}
  </section>

  <section class="card">
    <h2>Pipeline Steps</h2>
    <ul class="steps">
      {#each steps as s}
        <li class={`step ${s.status}`}>
          <span class="idx">#{s.index}</span>
          <span class="label">{s.label}</span>
          <span class="state">{s.status}</span>
          {#if s.detail}
            <span class="detail">{s.detail}</span>
          {/if}
        </li>
      {/each}
    </ul>
  </section>

  <section class="card">
    <h2>Logs</h2>
    <div class="logbox">
      {#if logs.length === 0}
        <div class="muted">No logs yet</div>
      {:else}
        {#each logs as line}
          <div class="logline">{line}</div>
        {/each}
      {/if}
    </div>
  </section>

  <section class="card">
    <h2>Result</h2>
    {#if resultData}
      <pre class="result">{JSON.stringify(resultData, null, 2)}</pre>
    {:else}
      <p class="muted">No result yet</p>
    {/if}
  </section>
</main>

<style>
  :global(body) {
    margin: 0;
    font-family: Inter, system-ui, Arial, sans-serif;
    background: #0b1020;
    color: #e6edf3;
  }

  .page {
    max-width: 960px;
    margin: 24px auto;
    padding: 0 16px 40px;
    display: grid;
    gap: 16px;
  }

  .card {
    background: #111a2e;
    border: 1px solid #27324a;
    border-radius: 12px;
    padding: 16px;
  }

  h1, h2 {
    margin: 0 0 8px;
    font-weight: 600;
  }

  .muted {
    color: #9fb0cc;
    margin: 0 0 8px;
  }

  .row {
    display: grid;
    gap: 6px;
    margin: 10px 0;
  }

  label {
    font-size: 14px;
    color: #c4d1e8;
  }

  .input {
    background: #0b1324;
    color: #e6edf3;
    border: 1px solid #2a3855;
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 14px;
  }

  .actions {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 12px;
    flex-wrap: wrap;
  }

  .btn {
    background: #2563eb;
    border: 1px solid #3b82f6;
    color: #fff;
    border-radius: 8px;
    padding: 9px 12px;
    cursor: pointer;
  }

  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-secondary {
    background: #1f2937;
    border-color: #374151;
  }

  .status-dot {
    font-size: 13px;
    padding: 4px 8px;
    border-radius: 999px;
    border: 1px solid;
  }

  .status-dot.ok {
    color: #86efac;
    border-color: #166534;
    background: #052e16;
  }

  .status-dot.bad {
    color: #fca5a5;
    border-color: #7f1d1d;
    background: #2b0d0d;
  }

  .status-text {
    color: #cbd5e1;
    font-size: 14px;
  }

  .error {
    color: #fda4af;
    margin-top: 10px;
  }

  .steps {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    gap: 8px;
  }

  .step {
    display: grid;
    grid-template-columns: 52px 1fr 100px;
    gap: 10px;
    align-items: center;
    background: #0b1324;
    border: 1px solid #26324a;
    border-radius: 8px;
    padding: 8px 10px;
  }

  .step .idx {
    color: #93c5fd;
    font-weight: 600;
  }

  .step .state {
    text-transform: lowercase;
    font-size: 13px;
    color: #cbd5e1;
    justify-self: end;
  }

  .step .detail {
    grid-column: 1 / -1;
    color: #9fb0cc;
    font-size: 13px;
  }

  .step.running {
    border-color: #1d4ed8;
  }

  .step.done {
    border-color: #166534;
  }

  .step.pending {
    opacity: 0.8;
  }

  .logbox {
    background: #0b1324;
    border: 1px solid #26324a;
    border-radius: 8px;
    padding: 10px;
    max-height: 220px;
    overflow: auto;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 12px;
  }

  .logline {
    padding: 2px 0;
    border-bottom: 1px dotted #22314d;
  }

  .logline:last-child {
    border-bottom: 0;
  }

  .result {
    background: #0b1324;
    border: 1px solid #26324a;
    border-radius: 8px;
    padding: 12px;
    overflow: auto;
    margin: 0;
    color: #dbeafe;
  }
</style>