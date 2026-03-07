// Injected before Google Meet loads.
// Monkey-patches RTCPeerConnection to intercept incoming audio tracks,
// routes PCM (Float32, 16 kHz, mono) over a WebSocket to the Python audio server.

(() => {
  const WS_URL = `ws://localhost:${window.__GARFIELD_WS_PORT || 9001}`;
  let ws = null;
  let connected = false;
  const trackedTracks = new Set();

  function ensureWebSocket() {
    if (ws && connected) return;
    ws = new WebSocket(WS_URL);
    ws.binaryType = "arraybuffer";
    ws.onopen = () => {
      connected = true;
      console.log("[garfield] WebSocket connected to", WS_URL);
    };
    ws.onclose = () => {
      connected = false;
      console.log("[garfield] WebSocket closed");
    };
    ws.onerror = (e) => {
      connected = false;
      console.error("[garfield] WebSocket error", e);
    };
  }

  function captureTrack(track) {
    if (trackedTracks.has(track.id)) return;
    trackedTracks.add(track.id);
    console.log("[garfield] Capturing audio track:", track.id);

    const ctx = new AudioContext({ sampleRate: 16000 });
    const source = ctx.createMediaStreamSource(new MediaStream([track]));

    // Use ScriptProcessorNode (deprecated but widely supported; AudioWorklet
    // requires a separate module file which is hard to inject).
    const processor = ctx.createScriptProcessor(4096, 1, 1);
    processor.onaudioprocess = (e) => {
      if (!connected) return;
      const pcm = e.inputBuffer.getChannelData(0);
      // Send raw Float32 PCM as binary
      ws.send(pcm.buffer.slice(0));
    };

    source.connect(processor);
    processor.connect(ctx.destination);

    track.addEventListener("ended", () => {
      console.log("[garfield] Track ended:", track.id);
      processor.disconnect();
      source.disconnect();
      ctx.close();
    });
  }

  // Monkey-patch RTCPeerConnection
  const OrigRTCPeerConnection = window.RTCPeerConnection;
  window.RTCPeerConnection = function (...args) {
    const pc = new OrigRTCPeerConnection(...args);

    pc.addEventListener("track", (event) => {
      ensureWebSocket();
      for (const track of event.streams.flatMap((s) => s.getAudioTracks())) {
        captureTrack(track);
      }
      if (event.track && event.track.kind === "audio") {
        captureTrack(event.track);
      }
    });

    return pc;
  };
  // Copy static properties / prototype
  window.RTCPeerConnection.prototype = OrigRTCPeerConnection.prototype;
  window.RTCPeerConnection.generateCertificate =
    OrigRTCPeerConnection.generateCertificate;

  // Fallback: if no tracks captured after 30s, try getDisplayMedia
  setTimeout(() => {
    if (trackedTracks.size > 0) return;
    console.log("[garfield] No tracks captured via RTC, trying getDisplayMedia fallback");
    ensureWebSocket();
    navigator.mediaDevices
      .getDisplayMedia({ audio: true, video: false })
      .then((stream) => {
        for (const track of stream.getAudioTracks()) {
          captureTrack(track);
        }
      })
      .catch((err) => {
        console.error("[garfield] getDisplayMedia fallback failed:", err);
      });
  }, 30000);

  console.log("[garfield] Audio capture script loaded, WS target:", WS_URL);
})();
