# Corner-guarded Scale2x (numpy, vectorized)

Naive Scale2x smooths *every* diagonal, which rounds 90° corners — machine-block
windows/frames/bars become "squircles", stone noise becomes blobs. The fix is a
**corner guard**: only smooth when the diagonal actually *continues* (`NE != SW` for
top-left/bottom-right outputs, `NW != SE` for the other two). Straight edges + corners
stay crisp; true diagonals still smooth.

## Code (the whole trick)

```python
def eq(a, b):
    return np.all(a == b, axis=-1)[..., None]  # (H,W,1) broadcasts over channels

def scale2x(arr):  # arr: HxWxC uint8
    H, W, C = arr.shape
    p = np.pad(arr, ((1,1),(1,1),(0,0)), mode="edge")
    NW=p[:-2,:-2]; N=p[:-2,1:-1]; NE=p[:-2,2:]
    W_=p[1:-1,:-2]; P=p[1:-1,1:-1]; E=p[1:-1,2:]
    SW=p[2:,:-2];  S=p[2:,1:-1];  SE=p[2:,2:]
    e0=np.where(eq(W_,N)&~eq(W_,S)&~eq(N,E)&~eq(NE,SW),W_,P)   # top-left
    e1=np.where(eq(N,E)&~eq(N,W_)&~eq(E,S)&~eq(NW,SE),N,P)     # top-right
    e2=np.where(eq(W_,S)&~eq(W_,N)&~eq(S,E)&~eq(NW,SE),W_,P)   # bottom-left
    e3=np.where(eq(S,E)&~eq(S,W_)&~eq(E,N)&~eq(NE,SW),S,P)     # bottom-right
    o=np.empty((H*2,W*2,C),dtype=arr.dtype)
    o[0::2,0::2]=e0; o[0::2,1::2]=e1; o[1::2,0::2]=e2; o[1::2,1::2]=e3
    return o
```

## Two findings that matter

- **Pure nearest-neighbor 2x is pointless as a resource pack.** Minecraft already
  renders 16x textures with nearest upscale at draw time, so a plain 2x pack looks
  identical to vanilla. The *smoothing* is the entire value; the corner guard is what
  stops it from distorting geometry.
- **Verify an *item* AND a *machine/tech block* before the full batch.** Items can look
  fine while geometric blocks are silently distorted — corner-rounding only shows on
  rectangular windows/frames. Build a before/after montage and eyeball both.
