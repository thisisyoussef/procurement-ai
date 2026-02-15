"""Endpoint to generate realistic example procurement requests via LLM."""

import random

from fastapi import APIRouter

from automotive.core.llm import call_haiku

router = APIRouter(tags=["automotive-generate"])

EXAMPLE_CATEGORIES = [
    "stamping", "die-casting", "injection molding", "CNC machining",
    "forging", "extrusion", "powder metallurgy", "sheet metal forming",
    "welding assemblies", "rubber/sealing components",
]

EXAMPLE_PARTS = [
    "brake mounting brackets", "EV battery housings", "engine valve covers",
    "transmission gear blanks", "steering knuckles", "suspension control arms",
    "turbocharger turbine housings", "exhaust manifold flanges",
    "door hinge assemblies", "seat frame components", "fuel rail assemblies",
    "differential housings", "wheel hub bearings", "ABS sensor brackets",
    "electric motor end bells", "inverter heat sinks",
]


@router.post("/generate-example")
async def generate_example_request() -> dict:
    """Generate a realistic automotive procurement request using Haiku."""
    category = random.choice(EXAMPLE_CATEGORIES)
    part = random.choice(EXAMPLE_PARTS)

    system = (
        "You are a procurement engineer at an automotive OEM or Tier 1 supplier. "
        "Generate a realistic, detailed supplier sourcing request in 2-4 sentences. "
        "Include: the specific part/component, manufacturing process, material, "
        "annual volume, required certifications (e.g. IATF 16949, ISO 14001), "
        "geographic preferences, and any special requirements. "
        "Make it sound natural, like someone typing into a procurement tool. "
        "Vary the tone — sometimes urgent, sometimes exploratory, sometimes very technical. "
        "Do NOT use bullet points or headers. Just plain conversational text."
    )

    messages = [
        {
            "role": "user",
            "content": (
                f"Generate a procurement request related to {category} for {part}. "
                "Make it unique and realistic. Just output the request text, nothing else."
            ),
        }
    ]

    response = await call_haiku(system=system, messages=messages, max_tokens=300)
    text = response.content[0].text.strip()

    return {"example_request": text}
