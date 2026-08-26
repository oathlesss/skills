# Twitch IRC chat + follower/sub alerts — working patterns

## Twitch IRC chat connector (verified in session)
WebSocket to Twitch IRC (no library needed). IRCv3 tags carry `display-name` and per-user `color`.

```js
function connectTwitch() {
  const channel = params.get("channel") || CFG.channel;
  const token = params.get("chat_token") || CFG.chat_token;
  if (!channel || !token) return;
  const nick = (params.get("nick") || CFG.nick || channel).toLowerCase();
  let ws = new WebSocket("wss://irc-ws.chat.twitch.tv:443");
  ws.onopen = () => {
    ws.send("CAP REQ :twitch.tv/tags twitch.tv/commands");
    ws.send("PASS oauth:" + token.replace(/^oauth:/i, ""));
    ws.send("NICK " + nick);
    ws.send("JOIN #" + channel.toLowerCase());
  };
  ws.onmessage = (e) => String(e.data).split("\r\n").forEach((l) => handleIrc(l, ws));
  ws.onerror = () => ws.close();
  ws.onclose = () => setTimeout(connectTwitch, 5000);   // auto-reconnect
}

function handleIrc(line, ws) {
  if (!line) return;
  if (line.startsWith("PING")) { ws.send("PONG :tmi.twitch.tv"); return; }
  let rest = line, tags = {};
  if (line.startsWith("@")) {                            // IRCv3 tags prefix
    const sp = line.indexOf(" ");
    line.slice(1, sp).split(";").forEach((kv) => {
      const i = kv.indexOf("=");
      if (i > 0) tags[kv.slice(0, i)] = kv.slice(i + 1);
    });
    rest = line.slice(sp + 1);
  }
  const idx = rest.indexOf("PRIVMSG");
  if (idx === -1) return;
  const mi = rest.indexOf(":", idx + "PRIVMSG".length);  // message after 2nd colon
  if (mi === -1) return;
  addChat((tags["display-name"] || "").trim() || "user", rest.slice(mi + 1), tags["color"] || "#c0c6d0");
}
```

Notes:
- Token is **chat-scoped** OAuth (e.g. twitchtokengenerator.com). Never commit a real `chat_token` — keep it commented/empty in config.js.
- `PING` → `PONG :tmi.twitch.tv` is required to stay connected. Reconnect on close.

## postMessage protocol (built; works for iframe-parent bridging)
```js
window.postMessage({ type: "follower", name: "X" }, "*");   // updates latest-follower pill + fires alert
window.postMessage({ type: "sub", name: "X", tier: 2 }, "*");
window.postMessage({ type: "chat", user: "X", message: "hi", color: "#fff" }, "*");
window.postMessage({ type: "latest", name: "X" }, "*");
window.postMessage({ title: "Raid", message: "10 viewers!" }, "*");  // generic
```

## StreamElements / Streamlabs wiring (write the snippet when requested)
- **Caveat:** OBS browser sources are separate CEF instances and cannot `postMessage` each other directly. So for these services the standard approach is to make the overlay itself the "custom widget" and listen to their SDK (`onEventReceived`) inside the page, rather than bridging two sources.
- Relevant StreamElements listeners: `follower-latest`, `subscriber-latest`, `raid-latest`, `host-latest`, `message` (chat). The exact forwarding snippet should be written against the SDK version the user is on — confirm before generating.
