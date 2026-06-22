# NeoForge AttachmentType Patterns

Reusable patterns for attaching persistent state to chunks, players, and worlds in NeoForge 1.21.x.

## Per-Chunk State with Dirty Tracking

Used for systems that need per-chunk data that changes slowly (aura, vis, flux, taint levels).

### Attachment Definition

```java
public static final Supplier<AttachmentType<MyChunkData>> MY_DATA =
    ATTACHMENT_TYPES.register("my_data",
        () -> AttachmentType.builder(MyChunkData::new)
                .serialize(MyChunkData.CODEC).build());
```

### Data Class with Dirty Flag

```java
public class MyChunkData {
    private boolean dirty = false;

    public boolean isDirty() { return dirty; }
    public void clearDirty() { dirty = false; }

    // Mutators set dirty = true when values change
    public void setValue(int v) {
        if (this.value != v) {
            this.value = v;
            dirty = true;
        }
    }
}
```

### Ticking and Syncing

Tick all chunks near players (not all loaded chunks — `ChunkMap.getChunks()` is protected in 1.21.x):

```java
@SubscribeEvent
public static void onLevelTick(LevelTickEvent.Post event) {
    if (!(event.getLevel() instanceof ServerLevel level)) return;
    if (level.getGameTime() % 20 != 0) return; // once per second

    // Collect chunks within view distance of each player
    Set<ChunkPos> toTick = new HashSet<>();
    int viewDist = level.getServer().getPlayerList().getViewDistance();
    for (ServerPlayer player : level.players()) {
        ChunkPos center = player.chunkPosition();
        for (int dx = -viewDist; dx <= viewDist; dx++)
            for (int dz = -viewDist; dz <= viewDist; dz++)
                toTick.add(new ChunkPos(center.x + dx, center.z + dz));
    }

    for (ChunkPos pos : toTick) {
        LevelChunk chunk = level.getChunkSource().getChunkNow(pos.x, pos.z);
        if (chunk == null) continue;

        var data = chunk.getData(MY_DATA.get());
        data.tick();

        if (data.isDirty()) {
            data.clearDirty();
            chunk.setData(MY_DATA.get(), data); // persist
            syncToTrackers(level, chunk, data);
        }
    }
}

private static void syncToTrackers(ServerLevel level, LevelChunk chunk, MyChunkData data) {
    var packet = new MySyncPacket(chunk.getPos().x, chunk.getPos().z, data.serialize());
    PacketDistributor.sendToPlayersTrackingChunk(level, chunk.getPos(), packet);
}
```

### Client-Side Cache

Use a bounded LRU cache for client-side chunk data:

```java
private static final Map<Long, int[]> cache = new LinkedHashMap<>(16, 0.75f, true) {
    @Override
    protected boolean removeEldestEntry(Map.Entry<Long, int[]> eldest) {
        return size() > MAX_CACHED_ENTRIES; // e.g. 256
    }
};
```

## Key Gotchas

1. **`ChunkMap.getChunks()` is protected** — can't iterate all loaded chunks directly. Use `getChunkNow()` with coordinates from player view distance instead.
2. **`chunk.setData()` must be called** after mutation or the attachment won't persist to disk.
3. **Don't sync every tick** — use a dirty flag and tick once per second (gameTime % 20). For fast-changing data, consider syncing at lower frequency (every 5 seconds).
4. **`PacketDistributor.sendToPlayersTrackingChunk(level, chunkPos, packet)`** is the correct method for chunk-scoped sync in 1.21.x — it sends to all players with that chunk loaded.
