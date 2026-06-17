# Discord PrivilegedIntentsRequired Error Pattern

## Full traceback (from journalctl)

```
discord.errors.PrivilegedIntentsRequired: Shard ID None is requesting privileged intents
that have not been explicitly enabled in the developer portal. It is recommended to go to
https://discord.com/developers/applications/ and explicitly enable the privileged intents
within your application's page. If this is not possible, then consider disabling the
privileged intents instead.

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File ".../discord/client.py", line 851, in start
    await self.connect(reconnect=reconnect)
  File ".../discord/client.py", line 775, in connect
    raise PrivilegedIntentsRequired(exc.shard_id) from None
```

## Misleading gateway summary

The `hermes gateway status` output only shows:
```
ERROR gateway.run: ✗ discord error: discord connect timed out after 30s
WARNING gateway.run: Reconnect discord error: discord connect timed out after 30s, next retry in 60s
```

The "timed out" message is misleading — the connection succeeds but Discord immediately rejects it with `PrivilegedIntentsRequired`, and the async exception isn't propagated to the gateway's reconnect loop.

## Finding the real error

```bash
journalctl --user -u hermes-gateway.service --no-pager -n 100 | grep -A5 Privileged
```

Or look for `discord.errors.PrivilegedIntentsRequired` in the full journal output.

## Fix

Go to Discord Developer Portal → your app → Bot → Privileged Gateway Intents → toggle on:
- Message Content Intent
- Server Members Intent  
- Presence Intent

Then `hermes gateway restart`.