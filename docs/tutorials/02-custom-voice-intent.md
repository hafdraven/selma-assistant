# Tutorial 2: Custom Voice Intent

The `selma.voice` gateway ships with nine built-in intents, but the real power
is extensibility: you can register your own intent handler on the router and
the gateway will dispatch to it just like the built-ins. This tutorial walks
through wiring up the full gateway stack, writing a custom intent, registering
it, and testing it with multiple assistants.

> **Prerequisites**: Complete the [getting-started guide](../getting-started.md)
> and ideally [Tutorial 1](01-reminders-and-scheduling.md) for familiarity with
> the life assistant.

## What you will build

A custom `WeatherIntent` that accepts a `city` slot, looks up a (mocked)
forecast, and returns a spoken response. You will test it through both the
Alexa and Google Home adapters using the same gateway instance.

## How the gateway is wired

`VoiceGateway.__init__` creates an internal `VoiceRouter` and registers the
nine built-in intents on it. The router is not exposed as a constructor
parameter — you cannot inject it. To register a custom intent, you need to
access the router **before** the built-in intents are registered, or register
on a router you control.

The cleanest pattern is to construct the `VoiceRouter` yourself, register both
the built-in intents and your custom intent on it, then construct the gateway
to use that router. However, `VoiceGateway` does not accept an external router.

The practical approach: construct a `VoiceRouter` with a `VoiceContext`,
register your custom intent on it, register the built-in intents on it, and
dispatch directly — bypassing `VoiceGateway` when you need custom intents. For
production use you would subclass or wrap the gateway; for this tutorial we
demonstrate the direct router pattern, which is the same dispatch path the
gateway uses.

## Step 1 — Set up the subsystems

The `VoiceContext` bundles references to the three Selma subsystems. Every
intent handler receives it as its second argument.

```python
from selma.memory import MemoryAPI
from selma.memory.backends.embedded import EmbeddedOxigraph
from selma.life import LifeAssistant
from selma.agents import AgentsAssistant
from selma.voice import VoiceContext

memory = MemoryAPI(EmbeddedOxigraph())
life = LifeAssistant(memory)
agents = AgentsAssistant(memory)
context = VoiceContext(memory=memory, life=life, agents=agents)
```

## Step 2 — Define a custom intent handler

An intent handler is a plain function with the signature
`handler(slots: dict[str, str], ctx: VoiceContext) -> VoiceResponse`. The
router catches `MissingSlotError` and maps it to a friendly "I need a [slot] to
do that" message, so use `require_slots` for mandatory slots.

```python
from selma.voice import VoiceResponse
from selma.voice.intents import require_slots

# A mock weather lookup.  In a real skill you would call a weather API.
_FORECASTS = {
    "seattle": "Rainy, 12°C",
    "portland": "Cloudy, 14°C",
    "san francisco": "Foggy, 16°C",
}

def handle_weather(slots: dict[str, str], ctx: VoiceContext) -> VoiceResponse:
    require_slots(slots, "city")
    city = slots["city"].lower()
    forecast = _FORECASTS.get(city, "I don't have a forecast for that city.")
    return VoiceResponse(
        f"In {city}: {forecast}.",
        card={"city": city, "forecast": forecast},
    )
```

The handler receives the `VoiceContext` even if it does not use it — your
custom intent can call `ctx.memory.recall(...)`, `ctx.life.reminders.create(...)`,
or any other subsystem method, just like the built-in intents do.

## Step 3 — Register on the router

Construct a `VoiceRouter` with the context, register the built-in intents, then
register your custom intent:

```python
from selma.voice import VoiceRouter, register_builtin_intents

router = VoiceRouter(context)
register_builtin_intents(router)
router.register("WeatherIntent", handle_weather)
```

The registration order does not matter — `register` overwrites any prior handler
for the same intent name, and built-in names do not collide with custom names as
long as you pick a unique intent name.

## Step 4 — Test with the Alexa adapter

The `AlexaAdapter` parses the Alexa request format and formats the response back.
You can use it directly for testing:

```python
from selma.voice import AlexaAdapter

alexa = AlexaAdapter()

alexa_request = {
    "request": {
        "intent": {
            "name": "WeatherIntent",
            "slots": {
                "city": {"value": "Seattle"},
            },
        },
    },
}

vr = alexa.parse_request(alexa_request)
print("intent:", vr.intent, "slots:", vr.slots)
# intent: WeatherIntent slots: {'city': 'Seattle'}

resp = router.dispatch(vr.intent, vr.slots)
print("response text:", resp.response_text)
# response text: In seattle: Rainy, 12°C.

alexa_out = alexa.format_response(resp)
print(alexa_out)
# {'response': {'outputSpeech': {'type': 'PlainText',
#  'text': 'In seattle: Rainy, 12°C.'}, 'card': {'city': 'seattle',
#  'forecast': 'Rainy, 12°C'}}}
```

## Step 5 — Test with the Google Home adapter

The same router, the same handler — just a different adapter:

```python
from selma.voice import GoogleHomeAdapter

google = GoogleHomeAdapter()

google_request = {
    "intent": "WeatherIntent",
    "params": {"city": "Portland"},
}

vr = google.parse_request(google_request)
resp = router.dispatch(vr.intent, vr.slots)
google_out = google.format_response(resp)
print(google_out)
# {'fulfillmentText': 'In portland: Cloudy, 14°C.',
#  'payload': {'city': 'portland', 'forecast': 'Cloudy, 14°C'}}
```

## Error handling

The router maps three failure cases to fixed friendly responses, so handler
exceptions never escape `dispatch`:

| Failure | Response |
|---------|----------|
| Unknown intent | "I don't know how to do that yet" |
| `MissingSlotError` | "I need a [slot] to do that" |
| Any other exception | "Something went wrong" |

Test the missing-slot case:

```python
resp = router.dispatch("WeatherIntent", {})
print(resp.response_text)
# I need a city to do that
```

## Complete runnable script

Save as `custom_intent_tutorial.py` and run with `python custom_intent_tutorial.py`.

```python
"""Tutorial 2: adding a custom voice intent."""
from __future__ import annotations

from selma.memory import MemoryAPI
from selma.memory.backends.embedded import EmbeddedOxigraph
from selma.life import LifeAssistant
from selma.agents import AgentsAssistant
from selma.voice import (VoiceContext, VoiceRouter, VoiceResponse,
                         register_builtin_intents,
                         AlexaAdapter, GoogleHomeAdapter)
from selma.voice.intents import require_slots


# -- Mock weather data -------------------------------------------------------

_FORECASTS = {
    "seattle": "Rainy, 12°C",
    "portland": "Cloudy, 14°C",
    "san francisco": "Foggy, 16°C",
}


# -- Custom intent handler ---------------------------------------------------

def handle_weather(slots: dict[str, str], ctx: VoiceContext) -> VoiceResponse:
    """Look up a (mocked) forecast for the requested city."""
    require_slots(slots, "city")
    city = slots["city"].lower()
    forecast = _FORECASTS.get(city, "I don't have a forecast for that city.")
    return VoiceResponse(
        f"In {city}: {forecast}.",
        card={"city": city, "forecast": forecast},
    )


# -- Main --------------------------------------------------------------------

def main() -> None:
    # 1. Set up the subsystems and voice context.
    memory = MemoryAPI(EmbeddedOxigraph())
    life = LifeAssistant(memory)
    agents = AgentsAssistant(memory)
    context = VoiceContext(memory=memory, life=life, agents=agents)

    # 2. Build the router, register built-ins, then the custom intent.
    router = VoiceRouter(context)
    register_builtin_intents(router)
    router.register("WeatherIntent", handle_weather)

    # 3. Test with the Alexa adapter.
    print("=== Alexa ===")
    alexa = AlexaAdapter()
    alexa_request = {
        "request": {
            "intent": {
                "name": "WeatherIntent",
                "slots": {"city": {"value": "Seattle"}},
            },
        },
    }
    vr = alexa.parse_request(alexa_request)
    print("  parsed:", vr.intent, vr.slots)
    resp = router.dispatch(vr.intent, vr.slots)
    print("  text:", resp.response_text)
    print("  card:", resp.card)
    print("  alexa output:", alexa.format_response(resp))

    # 4. Test with the Google Home adapter.
    print("\n=== Google Home ===")
    google = GoogleHomeAdapter()
    google_request = {
        "intent": "WeatherIntent",
        "params": {"city": "Portland"},
    }
    vr = google.parse_request(google_request)
    resp = router.dispatch(vr.intent, vr.slots)
    print("  text:", resp.response_text)
    print("  google output:", google.format_response(resp))

    # 5. Test the missing-slot error mapping.
    print("\n=== Missing slot ===")
    resp = router.dispatch("WeatherIntent", {})
    print("  text:", resp.response_text)
    # I need a city to do that

    # 6. Test the unknown-intent error mapping.
    print("\n=== Unknown intent ===")
    resp = router.dispatch("NonexistentIntent", {})
    print("  text:", resp.response_text)
    # I don't know how to do that yet

    # 7. Verify a built-in intent still works alongside the custom one.
    print("\n=== Built-in DescribeIntent ===")
    resp = router.dispatch("DescribeIntent", {})
    print("  text:", resp.response_text)

    print("\nDone.")


if __name__ == "__main__":
    main()
```

## Next steps

- [Tutorial 3: Custom Agent](03-custom-agent.md) — write an executor and
  run a task autonomously.
- [Voice API reference](../api-reference/voice.md) — full adapter, router, and
  gateway signatures.
- [Voice commands cheat sheet](../voice-commands.md) — all nine built-in intents
  and the four assistant request formats at a glance.