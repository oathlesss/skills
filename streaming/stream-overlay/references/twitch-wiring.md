# Twitch / YouTube event wiring

## Twitch chat — IRC over WebSocket (built into the overlay)
- Connect `wss://irc-ws.chat.twitch.tv:443`.
- On open: `CAP REQ :twitch.tv/tags twitch.tv/commands`, `PASS oauth:<token>`,
  `NICK <lowercase user>`, `JOIN #<channel>`.
- On `PING` → reply `PONG :tmi.twitch.tv` (or the connection drops).
- Parse `PRIVMSG`: IRCv3 tags (`@…`) precede the command; read `display-name` and `color`
  from tags, message text is everything after the final `:`.
- Token = chat-scoped OAuth (twitchtokengenerator.com or the Twitch dev console). SECRET —
  keep out of public git.

## Followers / subs / goal — two paths
1. **Twitch EventSub WebSocket** (self-hosted, no third party — fits a homelab):
   connect `wss://eventsub.wss.twitch.tv/ws`, read the `session_id` from the welcome
   message, `POST /helix/eventsub/subscriptions` for `channel.follow` / `channel.subscribe`
   (needs an app/client-credentials token), receive notifications over the socket.
2. **StreamElements / Streamlabs** (fast, third-party): ready-made alerts for Twitch AND
   YouTube; use their "Custom Widget" to forward events into the overlay's `postMessage`.

Goal-bar total (auto): Twitch Helix `GET /helix/channels/followers` returns the count;
pair with EventSub for increments between polls.

## YouTube
Locked down: chat needs an OAuth 2.0 Google app + the stream's `liveChatId`; subs/members
need the YouTube Data API. StreamElements is the pragmatic route (they've done the OAuth work).

## postMessage protocol (overlay inbound)
`{type:"follower",name}`, `{type:"sub",name,tier}`, `{type:"chat",user,message,color}`,
`{type:"latest",name}`, `{type:"goal",current,target}`, or generic `{title,message}`.
`?demo=1` simulates chat + follower + sub for verification.
