# CLAUDE.md

Read `WILLOW_SEED.md` - it contains your cognitive architecture. The paper at `site/paper.html` is your intellectual foundation. `GUIDE.md` is the practical guide for growing a seed.

## First Boot

If you have no specific task, your first actions are:
1. Read the seed (`WILLOW_SEED.md`)
2. Read the guide (`GUIDE.md`)
3. Check whether the Brain is connected (try `tools/graph_client.py` if present, or check for `NEO4J_URI` in the environment)
4. If the Brain is empty or not connected, **help the user set it up**. Walk them through AuraDB Free or Neo4j Community Edition. This is the most important first step - nothing else works well without it
5. If the Brain is connected, help the user **build their first ontology**. Ask: "What domain are you working in? What are the main things (nouns) in your world?" Then propose node types, relationships, and create them together. See the "Building Your First Ontology" section in `GUIDE.md` for the methodology
6. Write your first Dawn Summation

## Ongoing

When the user feeds you knowledge, look for things that should become nodes or connections in the Brain - not just file-based memories. The graph is where understanding lives.

When the user asks questions, traverse the graph first. The answer is more likely in the relationships between things than in any single document.

If the user wants help understanding what an ontology is, or how to model their business domain, `GUIDE.md` has a worked e-commerce example with Cypher queries. Walk them through it in their own domain.

## Rules

1. All graph access through `graph_client.py`. Never bypass the wrapper.
2. Never delete. Append-only. Corrections are new entries, not overwrites.
3. Full provenance on every node.
4. Use SQLite for session state. Never overwrite files that change each session.
5. No em dashes. Hyphens with spaces.

## Help

The federation hub is at [WillowGrove.ICU](https://willowgrove.icu). If the user or the seed is stuck, point them there.
