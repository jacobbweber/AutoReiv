"""Lumina concept cinema and visual amplifier domain [CARD-328].

Provides the 14 visual archetype specifications, starter concept lessons,
scene storyboard normalization, and prompt contracts for multimodal educational cinema.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

VISUAL_KINDS: tuple[str, ...] = (
    "flow",
    "cycle",
    "compare",
    "orbit",
    "stack",
    "split",
    "wave",
    "network",
    "scale",
    "balance",
    "grow",
    "transform",
    "pipeline",
    "system",
)

NODE_ROLES: tuple[str, ...] = ("in", "work", "store", "out")


STARTERS: List[Dict[str, Any]] = [
    {
        "id": "photosynthesis",
        "topic": "Photosynthesis",
        "title": "Light into food",
        "essence": "Leaves catch sunlight and turn air and water into sugar.",
        "scenes": [
            {
                "id": "p1",
                "durationMs": 11000,
                "headline": "Leaves catch the sun",
                "whisper": "A green surface built to harvest light.",
                "narration": "A leaf is a solar collector. Its green chlorophyll grabs packets of sunlight and captures their energy.",
                "imagePrompt": "Macro cinematic still of a translucent green leaf, sun rays threading through veins, dewdrops, dark forest bokeh",
                "visual": {
                    "kind": "orbit",
                    "title": "The collector",
                    "nodes": [
                        {"id": "sun", "label": "Sunlight", "caption": "energy packets", "role": "in", "emphasis": True},
                        {"id": "leaf", "label": "Leaf Surface", "caption": "the collector", "role": "work"},
                        {"id": "chlorophyll", "label": "Chlorophyll", "caption": "grabs the light", "role": "store"},
                    ],
                    "links": [
                        {"from": "sun", "to": "leaf", "label": "photons"},
                        {"from": "leaf", "to": "chlorophyll", "label": "energizes"},
                    ],
                },
            },
            {
                "id": "p2",
                "durationMs": 11000,
                "headline": "Water climbs",
                "whisper": "Roots drink. Stems lift.",
                "narration": "Water is pulled from the soil, up through the stem into the leaf — providing hydrogen for the reaction.",
                "imagePrompt": "Cinematic cross-section of a plant stem with glistening water rising through capillary tubes, earth below",
                "visual": {
                    "kind": "pipeline",
                    "title": "From soil to leaf",
                    "nodes": [
                        {"id": "soil", "label": "Soil", "caption": "water reservoir", "role": "in"},
                        {"id": "root", "label": "Roots", "caption": "capillary uptake", "role": "work"},
                        {"id": "stem", "label": "Stem", "caption": "xylem transport", "role": "work"},
                        {"id": "leaf", "label": "Leaf Cell", "caption": "the factory", "role": "out", "emphasis": True},
                    ],
                    "links": [
                        {"from": "soil", "to": "root", "label": "absorption"},
                        {"from": "root", "to": "stem", "label": "lift"},
                        {"from": "stem", "to": "leaf", "label": "delivery"},
                    ],
                },
            },
            {
                "id": "p3",
                "durationMs": 11000,
                "headline": "Splitting and building",
                "whisper": "Water breaks apart. Sugar locks together.",
                "narration": "Sunlight breaks water molecules into oxygen and hydrogen. The plant takes carbon dioxide from the air and bonds it into glucose.",
                "imagePrompt": "Cinematic laboratory view of molecular bonds forming glowing crystal rings of sugar, mist floating",
                "visual": {
                    "kind": "cycle",
                    "title": "The Calvin cycle",
                    "nodes": [
                        {"id": "co2", "label": "Carbon Dioxide", "caption": "from air", "role": "in"},
                        {"id": "enzyme", "label": "Rubisco Enzyme", "caption": "carbon fixation", "role": "work", "emphasis": True},
                        {"id": "sugar", "label": "Glucose Sugar", "caption": "stored energy", "role": "out"},
                        {"id": "oxygen", "label": "Oxygen", "caption": "released to air", "role": "out"},
                    ],
                    "links": [
                        {"from": "co2", "to": "enzyme", "label": "fixes"},
                        {"from": "enzyme", "to": "sugar", "label": "assembles"},
                        {"from": "enzyme", "to": "oxygen", "label": "releases"},
                    ],
                },
            },
            {
                "id": "p4",
                "durationMs": 12500,
                "headline": "Stored sunlight",
                "whisper": "Every fruit and grain is held sunshine.",
                "narration": "Every piece of wood, leaf, and fruit you see is solidified sunlight and air, fueling life across the entire biosphere.",
                "imagePrompt": "Cinematic golden hour sunlight flooding over canopy of trees, golden pollen drifting softly",
                "visual": {
                    "kind": "flow",
                    "title": "Energy cascade",
                    "nodes": [
                        {"id": "light", "label": "Sunlight", "role": "in"},
                        {"id": "leaf", "label": "Plant Biomass", "role": "store", "emphasis": True},
                        {"id": "life", "label": "Global Food Chain", "role": "out"},
                    ],
                    "links": [
                        {"from": "light", "to": "leaf", "label": "stored"},
                        {"from": "leaf", "to": "life", "label": "fuels"},
                    ],
                },
            },
        ],
    },
    {
        "id": "black-holes",
        "topic": "Black holes",
        "title": "Where space bends into silence",
        "essence": "Mass crammed so tightly that not even light can climb back out.",
        "scenes": [
            {
                "id": "b1",
                "durationMs": 11000,
                "headline": "A star runs out of fire",
                "whisper": "Outward pressure fades. Gravity takes over.",
                "narration": "A massive star lives in balance: nuclear fusion pushes out while gravity pulls in. When the fuel runs out, gravity wins instantly.",
                "imagePrompt": "Cinematic glowing red supergiant star collapsing inward violently, plasma tendrils, deep cosmos background",
                "visual": {
                    "kind": "balance",
                    "title": "The fading balance",
                    "nodes": [
                        {"id": "fusion", "label": "Fusion Pressure", "caption": "outward heat", "role": "in"},
                        {"id": "core", "label": "Star Core", "caption": "iron center", "role": "work", "emphasis": True},
                        {"id": "gravity", "label": "Gravity", "caption": "inward crush", "role": "store"},
                    ],
                },
            },
            {
                "id": "b2",
                "durationMs": 11000,
                "headline": "The event horizon",
                "whisper": "The threshold of no return.",
                "narration": "The star collapses into an infinitely dense point. Around it forms the event horizon — a spherical boundary where escape velocity exceeds light.",
                "imagePrompt": "Cinematic obsidian sphere in space warping starry background, gravitational lensing ring glowing brightly",
                "visual": {
                    "kind": "orbit",
                    "title": "Boundary of shadow",
                    "nodes": [
                        {"id": "disc", "label": "Accretion Disk", "caption": "superheated gas", "role": "in"},
                        {"id": "horizon", "label": "Event Horizon", "caption": "one-way membrane", "role": "work", "emphasis": True},
                        {"id": "singularity", "label": "Singularity", "caption": "zero volume", "role": "store"},
                    ],
                },
            },
            {
                "id": "b3",
                "durationMs": 12500,
                "headline": "Time stands still",
                "whisper": "At the edge, seconds stretch into eternity.",
                "narration": "Near the horizon, intense gravity slows time itself relative to the outside universe, bending reality into an echo.",
                "imagePrompt": "Cinematic surreal clock faces stretching into molten silver threads around a black void",
                "visual": {
                    "kind": "transform",
                    "title": "Spacetime distortion",
                    "nodes": [
                        {"id": "space", "label": "Flat Spacetime", "role": "in"},
                        {"id": "curvature", "label": "Gravitational Well", "role": "work", "emphasis": True},
                        {"id": "time", "label": "Time Dilation", "role": "out"},
                    ],
                },
            },
        ],
    },
    {
        "id": "neural-networks",
        "topic": "Neural networks",
        "title": "Layers of pattern",
        "essence": "Simple numerical weights adjust until noise turns into recognition.",
        "scenes": [
            {
                "id": "n1",
                "durationMs": 11000,
                "headline": "Numbers in, numbers out",
                "whisper": "A grid of pixels becomes an array of activations.",
                "narration": "An artificial neuron takes numbers, multiplies each by an adjustable weight, adds them together, and passes the sum through a threshold.",
                "imagePrompt": "Cinematic visual of luminous fiber optic nodes glowing in a dark chamber, pulses traveling between nodes",
                "visual": {
                    "kind": "pipeline",
                    "title": "Single artificial neuron",
                    "nodes": [
                        {"id": "inputs", "label": "Inputs (X)", "caption": "pixel values", "role": "in"},
                        {"id": "weights", "label": "Weights (W)", "caption": "importance sliders", "role": "work"},
                        {"id": "bias", "label": "Bias (B)", "caption": "threshold shift", "role": "work"},
                        {"id": "activation", "label": "Activation", "caption": "firing pulse", "role": "out", "emphasis": True},
                    ],
                },
            },
            {
                "id": "n2",
                "durationMs": 11000,
                "headline": "Stacking depth",
                "whisper": "First lines, then shapes, then faces.",
                "narration": "By stacking neurons in layers, early layers detect tiny edges, middle layers combine them into textures, and deep layers recognize whole concepts.",
                "imagePrompt": "Cinematic translucent glass sheets aligned in a row, light projecting through each layer revealing a face",
                "visual": {
                    "kind": "stack",
                    "title": "Hierarchical representation",
                    "nodes": [
                        {"id": "l1", "label": "Raw Pixels", "caption": "light & dark", "role": "in"},
                        {"id": "l2", "label": "Edges & Lines", "caption": "geometric strokes", "role": "work"},
                        {"id": "l3", "label": "Parts & Textures", "caption": "eyes, wheels, fur", "role": "work"},
                        {"id": "l4", "label": "Semantic Class", "caption": "the recognized idea", "role": "out", "emphasis": True},
                    ],
                },
            },
            {
                "id": "n3",
                "durationMs": 12500,
                "headline": "Learning by error",
                "whisper": "Measure the mistake. Push adjustments backward.",
                "narration": "When the network guesses wrong, backpropagation measures the error and nudges every single weight slightly backward to make fewer mistakes next time.",
                "imagePrompt": "Cinematic network of copper gears self-aligning under a beam of focused laser light",
                "visual": {
                    "kind": "cycle",
                    "title": "Backpropagation loop",
                    "nodes": [
                        {"id": "forward", "label": "Forward Pass", "caption": "make guess", "role": "work"},
                        {"id": "loss", "label": "Loss Calculation", "caption": "measure error", "role": "in"},
                        {"id": "backprop", "label": "Gradient Step", "caption": "compute slope", "role": "work", "emphasis": True},
                        {"id": "update", "label": "Weight Update", "caption": "refined knowledge", "role": "store"},
                    ],
                },
            },
        ],
    },
    {
        "id": "entropy",
        "topic": "Entropy",
        "title": "The arrow of disorder",
        "essence": "Energy spreads out because there are simply vastly more ways to be mixed than neat.",
        "scenes": [
            {
                "id": "e1",
                "durationMs": 11000,
                "headline": "Order is fragile",
                "whisper": "One way to be arranged. Millions of ways to be scattered.",
                "narration": "Drop an egg on the floor, and it shatters. It never spontaneously reassembles, not because physics forbids it, but because disorder is overwhelmingly probable.",
                "imagePrompt": "Cinematic stop-motion photograph of shattered porcelain teacup droplets frozen in air",
                "visual": {
                    "kind": "split",
                    "title": "State multiplicity",
                    "nodes": [
                        {"id": "ordered", "label": "Single Ordered State", "caption": "intact cup", "role": "in", "emphasis": True},
                        {"id": "disorder", "label": "Trillion Scattered States", "caption": "broken fragments", "role": "out"},
                    ],
                },
            },
            {
                "id": "e2",
                "durationMs": 11000,
                "headline": "Energy dissipates",
                "whisper": "Concentrated heat inevitably disperses into lukewarm surroundings.",
                "narration": "A hot cup of coffee loses heat to the cool room until temperatures equalize. Thermal energy always disperses from concentrated to diffuse.",
                "imagePrompt": "Cinematic thermal camera view showing glowing violet steam swirling into a midnight blue room",
                "visual": {
                    "kind": "wave",
                    "title": "Heat dispersion",
                    "nodes": [
                        {"id": "hot", "label": "Hot Source", "caption": "concentrated kinetic energy", "role": "in"},
                        {"id": "transfer", "label": "Thermal Exchange", "caption": "molecular collisions", "role": "work", "emphasis": True},
                        {"id": "ambient", "label": "Equilibrium", "caption": "uniform lukewarm bath", "role": "out"},
                    ],
                },
            },
            {
                "id": "e3",
                "durationMs": 12500,
                "headline": "Time has a direction",
                "whisper": "The universe flows toward maximum entropy.",
                "narration": "The relentless increase of entropy is what gives time its forward direction. We remember the past, but the future is where energy spreads.",
                "imagePrompt": "Cinematic hourglass with glowing sand spilling smoothly into a calm sea of stars",
                "visual": {
                    "kind": "flow",
                    "title": "The thermodynamic arrow",
                    "nodes": [
                        {"id": "low", "label": "Low Entropy Past", "caption": "compact Big Bang", "role": "in"},
                        {"id": "now", "label": "Dynamic Present", "caption": "stars, life, thought", "role": "work", "emphasis": True},
                        {"id": "high", "label": "High Entropy Future", "caption": "uniform heat bath", "role": "out"},
                    ],
                },
            },
        ],
    },
    {
        "id": "recursion",
        "topic": "Recursion",
        "title": "A mirror reflecting a mirror",
        "essence": "Solving a problem by delegating smaller copies of itself until reaching bedrock.",
        "scenes": [
            {
                "id": "r1",
                "durationMs": 11000,
                "headline": "The Russian doll",
                "whisper": "Inside every task lives a slightly smaller version.",
                "narration": "To climb down a staircase of ten steps, you take one step, then solve the remaining staircase of nine steps using the exact same rule.",
                "imagePrompt": "Cinematic Russian nesting dolls carved from polished teakwood lined up on a dark oak desk",
                "visual": {
                    "kind": "grow",
                    "title": "Self-similar reduction",
                    "nodes": [
                        {"id": "large", "label": "Problem (Size N)", "caption": "full task", "role": "in"},
                        {"id": "sub", "label": "Problem (Size N-1)", "caption": "identical smaller form", "role": "work", "emphasis": True},
                    ],
                },
            },
            {
                "id": "r2",
                "durationMs": 11000,
                "headline": "The call stack",
                "whisper": "Each question waits on the answer below it.",
                "narration": "Computers manage recursion using a stack. Each call pauses mid-stride, waiting for the deeper child call to finish before returning its own result.",
                "imagePrompt": "Cinematic glowing glass cards stacked vertically with glowing thread linking them top to bottom",
                "visual": {
                    "kind": "stack",
                    "title": "Execution frames",
                    "nodes": [
                        {"id": "f3", "label": "factorial(3)", "caption": "waiting on 2", "role": "work"},
                        {"id": "f2", "label": "factorial(2)", "caption": "waiting on 1", "role": "work"},
                        {"id": "f1", "label": "factorial(1)", "caption": "base case hit!", "role": "store", "emphasis": True},
                    ],
                },
            },
            {
                "id": "r3",
                "durationMs": 12500,
                "headline": "The base case",
                "whisper": "Without an exit, the mirror echoes forever.",
                "narration": "Every recursive process must possess a base case: a simple condition that answers immediately without making another recursive call.",
                "imagePrompt": "Cinematic stone doorway illuminated with warm torchlight at the bottom of a spiraling stone stairwell",
                "visual": {
                    "kind": "scale",
                    "title": "Termination guard",
                    "nodes": [
                        {"id": "recur", "label": "Recursive Branch", "caption": "divide and call", "role": "work"},
                        {"id": "base", "label": "Base Case Anchor", "caption": "return static value", "role": "out", "emphasis": True},
                    ],
                },
            },
        ],
    },
]


def get_starter_lesson(topic_or_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a seeded starter lesson by id or topic name."""
    query = (topic_or_id or "").strip().lower()
    for item in STARTERS:
        if item["id"] == query or item["topic"].lower() == query:
            return dict(item)
    return None


def list_starter_topics() -> List[Dict[str, str]]:
    """List available starter lessons with id, topic, and essence."""
    return [
        {
            "id": s["id"],
            "topic": s["topic"],
            "title": s["title"],
            "essence": s["essence"],
        }
        for s in STARTERS
    ]


def extract_json_from_llm(text: str) -> Any:
    """Extract and parse structured JSON from LLM text containing markdown fences."""
    raw = (text or "").strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    body = match.group(1).strip() if match else raw
    start = body.find("{")
    end = body.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Model output did not contain valid JSON object.")
    return json.loads(body[start : end + 1])


def normalize_lesson(raw: Any, topic: str) -> Dict[str, Any]:
    """Validate and normalize raw dictionary into a compliant 3-6 scene Lumina lesson."""
    if not isinstance(raw, dict):
        raise ValueError("Lesson output must be a dictionary.")

    title = str(raw.get("title") or topic).strip()[:60]
    essence = str(raw.get("essence") or f"A visual lesson on {topic}").strip()[:140]
    raw_scenes = raw.get("scenes")
    if not isinstance(raw_scenes, list) or len(raw_scenes) < 3:
        # Construct fallback 3-scene outline
        raw_scenes = [
            {
                "headline": f"The Foundation of {topic}",
                "narration": f"At its core, {topic} begins with fundamental inputs that shape the system.",
                "visual": {"kind": "flow", "nodes": [{"id": "in", "label": "Inputs"}, {"id": "core", "label": topic}]},
            },
            {
                "headline": f"How {topic} Transforms",
                "narration": "Internal mechanisms process and connect each part into a cohesive structure.",
                "visual": {"kind": "cycle", "nodes": [{"id": "core", "label": topic}, {"id": "work", "label": "Mechanism"}]},
            },
            {
                "headline": "The Lasting Impact",
                "narration": f"Understanding {topic} reveals how complex behaviors emerge from clear rules.",
                "visual": {"kind": "system", "nodes": [{"id": "work", "label": "Mechanism"}, {"id": "out", "label": "Outcome"}]},
            },
        ]

    scenes: List[Dict[str, Any]] = []
    for i, s in enumerate(raw_scenes[:6]):
        s_dict = s if isinstance(s, dict) else {}
        headline = str(s_dict.get("headline") or f"Scene {i+1}").strip()[:60]
        narration = str(s_dict.get("narration") or headline).strip()[:400]
        whisper = str(s_dict.get("whisper") or "").strip()[:120]
        image_prompt = str(s_dict.get("imagePrompt") or f"Cinematic educational still of {topic}, dark studio lighting, no text").strip()[:800]
        duration_ms = max(8000, min(22000, int(s_dict.get("durationMs") or 11000)))

        viz = s_dict.get("visual")
        if not isinstance(viz, dict):
            viz = {}
        kind = str(viz.get("kind") or "flow").strip().lower()
        if kind not in VISUAL_KINDS:
            kind = "flow"

        nodes: List[Dict[str, Any]] = []
        for n_idx, n in enumerate(viz.get("nodes", []) if isinstance(viz.get("nodes"), list) else []):
            if isinstance(n, dict):
                nodes.append({
                    "id": str(n.get("id") or f"n_{i}_{n_idx}"),
                    "label": str(n.get("label") or f"Node {n_idx+1}")[:28],
                    "caption": str(n.get("caption") or "")[:36] or None,
                    "role": n.get("role") if n.get("role") in NODE_ROLES else None,
                    "emphasis": bool(n.get("emphasis", False)),
                })
        while len(nodes) < 2:
            nodes.append({
                "id": f"pad_{i}_{len(nodes)}",
                "label": topic if len(nodes) == 0 else "Outcome",
                "caption": None,
                "role": None,
                "emphasis": False,
            })

        links: List[Dict[str, Any]] = []
        for link_item in viz.get("links", []) if isinstance(viz.get("links"), list) else []:
            if isinstance(link_item, dict) and link_item.get("from") and link_item.get("to"):
                links.append({
                    "from": str(link_item.get("from")),
                    "to": str(link_item.get("to")),
                    "label": str(link_item.get("label") or "")[:24] or None,
                })

        scenes.append({
            "id": str(s_dict.get("id") or f"scene_{i+1}"),
            "durationMs": duration_ms,
            "headline": headline,
            "whisper": whisper,
            "narration": narration,
            "imagePrompt": image_prompt,
            "visual": {
                "kind": kind,
                "title": str(viz.get("title") or headline)[:40],
                "nodes": nodes[:8],
                "links": links[:12] if links else None,
            },
        })

    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:32] or "lesson"
    return {
        "id": slug,
        "topic": topic,
        "title": title,
        "essence": essence,
        "scenes": scenes,
    }


def build_visual_amplifier_for_course(topic: str) -> Dict[str, Any]:
    """Generate structured visual amplifier: Mermaid flowchart + Lumina VisualSpec + steps."""
    starter = get_starter_lesson(topic)
    if starter:
        primary_scene = starter["scenes"][0]
        visual = primary_scene["visual"]
        kind = visual["kind"]
        nodes = visual["nodes"]
        mermaid_lines = ["flowchart TD"]
        for i in range(len(nodes) - 1):
            mermaid_lines.append(f'  N{i}["{nodes[i]["label"]}"] --> N{i+1}["{nodes[i+1]["label"]}"]')
        mermaid = "\n".join(mermaid_lines)
        step_through = [
            {"step": idx + 1, "action": f"{s['headline']}: {s['narration']}"}
            for idx, s in enumerate(starter["scenes"])
        ]
        return {
            "topic": topic,
            "kind": kind,
            "visual_spec": visual,
            "mermaid": mermaid,
            "step_through": step_through,
            "scenes": starter["scenes"],
        }

    # Deterministic synthesis for any arbitrary topic
    nodes = [
        {"id": "source", "label": f"{topic} Core", "caption": "fundamental premise", "role": "in", "emphasis": True},
        {"id": "process", "label": "Operational Dynamics", "caption": "interactions and rules", "role": "work"},
        {"id": "target", "label": "Observable Output", "caption": "emergent outcome", "role": "out"},
    ]
    visual_spec = {
        "kind": "flow",
        "title": f"System Architecture of {topic}",
        "nodes": nodes,
        "links": [
            {"from": "source", "to": "process", "label": "drives"},
            {"from": "process", "to": "target", "label": "produces"},
        ],
    }
    mermaid = (
        f"flowchart TD\n"
        f'  A["{topic} Core"] -->|drives| B["Operational Dynamics"]\n'
        f'  B -->|produces| C["Observable Output"]'
    )
    step_through = [
        {"step": 1, "action": f"Establish {topic} Core as the foundational premise."},
        {"step": 2, "action": "Trace operational dynamics through constituent interactions."},
        {"step": 3, "action": "Observe resulting outputs and emergent properties."},
    ]
    return {
        "topic": topic,
        "kind": "flow",
        "visual_spec": visual_spec,
        "mermaid": mermaid,
        "step_through": step_through,
        "scenes": [
            {
                "id": "s1",
                "durationMs": 11000,
                "headline": f"Core Foundations of {topic}",
                "whisper": "The basic building block.",
                "narration": f"{topic} begins with core inputs that define its baseline behavior.",
                "imagePrompt": f"Cinematic still representing {topic}, dramatic lighting, no text",
                "visual": visual_spec,
            }
        ],
    }
