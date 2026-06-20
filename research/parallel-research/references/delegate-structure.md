# Delegate Task Call Structure — Concrete Example

This shows the exact shape for parallel web research delegation. Adapt the goal/context/toolsets per topic.

```python
delegate_task(tasks=[
    {
        "goal": "Research practical rainwater systems for toilet flushing from outdoor rain barrels. Find: specific pump models available in NL/BE, filtration requirements, mains switchover systems, plumbing approach, real prices and shops. Return structured summary with product names, prices, specs, and links.",
        "context": "User has rain barrels (2-4, ~400-1000L total) in Netherlands/Belgium. Has Home Assistant homelab, Docker, technically skilled. Rain barrels are outdoors. Need to supply water at domestic pressure to indoor appliances.",
        "toolsets": ["web", "terminal"]
    },
    {
        "goal": "Research using rain barrel water for horse drinking troughs. Find: water quality requirements, health risks (bacteria, algae, bird droppings), treatment options (UV, filtration, chemicals), auto-fill systems for gravity-fed setups, NL/BE regulations. Be thorough on health/safety — horse health is critical.",
        "context": "User has rain barrels at a property with horses. Wants to use rainwater to fill horse drinking troughs. Horses drink 20-50L/day each. Netherlands/Belgium climate.",
        "toolsets": ["web", "terminal"]
    }
])
```

## Key fields

| Field | Purpose | Required |
|-------|---------|----------|
| `goal` | Specific research question + desired output format | Yes |
| `context` | User setup, location, constraints, skill level | Yes — subagents have no memory |
| `toolsets` | `["web", "terminal"]` for web research | Yes — web_search unavailable otherwise |

## After delegation

1. `stat` any files the subagent claims to have written
2. Spot-check prices and claims against search result snippets in the summary
3. Write a synthesis file combining findings if subagents wrote separate reports
