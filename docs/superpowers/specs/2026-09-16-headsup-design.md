# Heads Up — Design Spec

**Tagline:** News happens. Heads Up tells you what it means for you — and handles it.

**Hackathon theme:** "Build an AI agent that solves a real problem in someone's day-to-day local life."

**One-liner for judges:** NewsBreak knows what's happening nearby. Heads Up knows whether it's *your* problem — and does something about it.

---

## 1. Problem and thesis

NewsBreak today: *"580 is jammed after a crash."* The user still has to figure out: does this touch my 9:00 school run? How much later should I leave? Should I set a reminder?

Heads Up closes that gap with one loop:

```
News happens  →  Does it affect me?  →  What should I do?
```

The unique asset is not the news; it is **hyperlocal, real-time context** crossed with **the user's own day** (calendar, home/work, preferences, the tools they already use). That crossing is where the agent lives.

Business angle (for the pitch, not the build): every action button on a card is an expressed **local intent** — buy a ticket, book a table, navigate to a cafe. NewsBreak moves from selling attention (ads) to routing intent (transactions / leads).

## 2. Constraints

| Constraint | Value |
|---|---|
| Race-day build time | 4 hours |
| Core devs | 2 |
| Pre-building | Allowed (**verify hackathon rules before Saturday** — some events restrict pre-built code to boilerplate/data) |
| Data | Public APIs only — no NewsBreak internal data |
| Demo surface | Telegram bot (proactive cards + inline action buttons + free-text follow-up) |
| Agent language | Python |
| LLM | DeepSeek via its OpenAI-compatible API; provider kept swappable |

## 3. Demo form: Telegram bot

Why Telegram over a web app or a chat-only agent:

- Bots can **push** messages proactively — the "proactive discovery" story is native, not simulated.
- **Inline keyboard buttons** = one-tap actions.
- A plain reply to a card = **follow-up conversation**, with the card as context.
- Zero UI code; judges use it on their own phone.
- Long-polling means no public URL is required. Runs from a laptop.

Telegram is the shipped **Channel** implementation, not the only possible one (see §4.3). WhatsApp Business API was deferred (approval latency, template-message restrictions). A projector-facing "god view" web page is a stretch goal (see §9).

## 4. Architecture

Two symmetric plug-in layers feed the agent core:

- **Sensors** — world-side sources. Many providers, one `LocalEvent` shape.
- **Integrations** — user-side services (where the user's day lives and where actions land). One Protocol per capability, many providers, chosen by config.

```
 WORLD SIDE                          AGENT CORE                              USER SIDE
┌──────────────┐  LocalEvent  ┌──────────────────┐  Impact  ┌────────────────┐  Card  ┌───────────────────────────┐
│ Sensors      │ ───────────▶ │ Relevance Engine │ ───────▶ │ Action Planner │ ─────▶ │ Integrations              │
│  511 traffic │              │ 1. rule prefilter│          │ LLM + tools    │        │  Channel   Telegram │ …   │
│  NWS weather │              │ 2. LLM judgment  │          │ built from the │ ◀───── │  Calendar  Google   │ …   │
│  Eventbrite  │              └────────┬─────────┘          │ registered     │ ctx    │  Maps      Google   │ …   │
│  RSS news    │                       │ ctx                │ integrations   │        │  Reminders scheduler│ …   │
│  Injector    │                       ▼                    └────────────────┘        │  Booking   open_url │ …   │
└──────────────┘              User Context (profile + Calendar + …)                    │  Profile   JSON     │ …   │
                                                                                       └───────────────────────────┘
```

Five core modules plus the two plug-in layers, connected only through Pydantic models. The models and the Protocols are the contract between the two developers.

### 4.1 Data model

```python
class LocalEvent(BaseModel):
    id: str                      # source-prefixed, used for dedupe
    source: str                  # "511" | "nws" | "eventbrite" | "rss" | "inject"
    type: Literal["traffic", "weather", "outage", "event", "closure", "news"]
    title: str
    summary: str
    lat: float
    lon: float
    radius_km: float             # area of effect
    starts_at: datetime
    ends_at: datetime | None
    severity: int                # 1–5, source-normalized
    url: str | None

class Impact(BaseModel):
    affected: bool
    why: str                     # one sentence, user-facing
    severity: Literal["low", "medium", "high"]
    confidence: float
    calendar_event_id: str | None  # which of the user's events is hit

class Action(BaseModel):
    id: str
    label: str                   # button text
    kind: Literal["remind", "navigate", "calendar_add", "open_url", "chat"]
    payload: dict

class Card(BaseModel):
    event_id: str
    headline: str
    impact: str
    detail: str | None           # e.g. ETA comparison, cafe list
    actions: list[Action]        # 1–3
```

### 4.2 Sensors (`headsup/sensors/`)

One poller per source, all returning `list[LocalEvent]`. APScheduler runs them every N minutes. Sources:

| Source | API | Key | Reliability | Notes |
|---|---|---|---|---|
| Traffic | 511.org SF Bay `traffic/events` | free token | good | real incidents; map `severity` |
| Weather alerts | `api.weather.gov/alerts?point=lat,lon` | none | excellent | first real source to wire |
| Events | Eventbrite Search or Ticketmaster Discovery | free key | good | filter by category + user prefs |
| Local news | Google News RSS (`?q=Oakland`) or local outlet RSS | none | ok | geo is fuzzy; LLM extracts location |
| Power outage | — | — | none | PG&E has no stable public API → **injector only** |
| School closure | — | — | none | **injector only** |

The **Injector** is a sensor too: it reads `scenarios/*.json` (one `LocalEvent` each) and emits on demand via CLI (`python -m headsup.inject 580_accident`) or a hidden Telegram command (`/demo 580`). Everything downstream is identical for real and injected events.

Adding a sensor = one file implementing `Sensor.poll() -> list[LocalEvent]` and one line in `integrations.yaml`.

### 4.3 Integrations (`headsup/integrations/`) — the user's own services

Each capability is a `typing.Protocol`. The planner's tools are generated from whatever is registered, so adding a provider never touches agent code. Selection lives in `integrations.yaml`:

```yaml
channel:   telegram
calendar:  google        # or: mock
maps:      google
reminders: scheduler
booking:   open_url
profile:   json
```

| Capability | Protocol methods | Shipped for the hackathon | Add later (same interface) |
|---|---|---|---|
| **Channel** — deliver cards, receive button taps and replies | `push(card)`, `edit(msg_id, text)`, `on_callback(fn)`, `on_reply(fn)` | Telegram (`python-telegram-bot`) | WhatsApp Cloud API, Lark, iMessage via Shortcuts, NewsBreak in-app push |
| **Calendar** — the user's day | `list_events(start, end)`, `free_slots(start, end, min_len)`, `insert_event(...)` | Google Calendar (OAuth), Mock (JSON) | Apple / CalDAV, Outlook Graph |
| **Maps** — routing and places | `route_eta(origin, dest, depart_at, avoid=None)`, `find_places(query, near, open_now)`, `geocode(text)` | Google Routes API + Places API (New) | Mapbox, Apple MapKit JS, HERE |
| **Reminders** — deferred nudges | `schedule(at, text)`, `cancel(id)` | Internal APScheduler → `Channel.push` | Google Tasks, Apple Reminders, Todoist |
| **Booking** — the intent → transaction hook | `checkout_url(event_or_place)`, later `reserve(...)` | `open_url` (Eventbrite / Ticketmaster / OpenTable deep links) | Eventbrite checkout, OpenTable/Resy, Uber deep link |
| **Profile** — home/work/school, commute, preferences, channel ids | `get()`, `update(patch)` | JSON file | NewsBreak account, inferred from calendar |

Design rules:
- A Protocol has **one shipped implementation plus Mock where the demo needs it**. Do not build a second real provider before Saturday; list it in the pitch as "same interface, one file".
- Every provider is a thin wrapper (≤ 60 lines) returning plain Pydantic models. No provider types leak into the agent core.
- `Channel` owns message-id ↔ card-id mapping so button callbacks and replies resolve to a `Card` regardless of messenger.

### 4.4 User Context (`headsup/context.py`)

Assembles what the Relevance Engine and Planner see about the user: `Profile` + `Calendar.list_events(now, now+24h)` + `Calendar.free_slots(...)`. It reads through the registered integrations; it holds no provider logic itself.

### 4.5 Relevance Engine (`headsup/relevance.py`) — "Does it affect me?"

Two stages. The first exists so the LLM only sees candidates, not the firehose.

**Stage 1 — rule prefilter (pure functions, unit-tested):**
1. Dedupe: `event.id` already in SQLite → drop.
2. Time: event window must intersect `[now, now + 24h]`.
3. Geo / route: event within `radius_km` of home, work, school, **or** any calendar event location in the next 24h, **or** (traffic only) inside the bounding corridor of the commute.
4. Type gate: `event` type only passes if the user has a free slot ≥ 2h overlapping the event.

**Stage 2 — LLM judgment (structured output → `Impact`):**
Prompt receives the event, the matching calendar entries, and the profile. Asked to decide `affected`, explain `why` in one user-facing sentence, and grade severity. `affected == false` or `confidence < 0.6` → drop, log, never push.

### 4.6 Action Planner (`headsup/planner.py`) — "What should I do?"

LLM with tools, output `Card`. Tools are the registered integrations' Protocol methods exposed 1:1 (each wrapper ≤ 30 lines):

| Tool | Backed by | Used by |
|---|---|---|
| `route_eta(...)` | `Maps` | traffic scenario: ETA with vs. without the incident |
| `find_places(...)` | `Maps` | outage scenario: cafes with Wi-Fi open tonight |
| `calendar_list(...)`, `free_slots(...)` | `Calendar` | all |
| `calendar_insert(...)` | `Calendar` | event scenario |
| `schedule_reminder(...)` | `Reminders` | traffic scenario |
| `checkout_url(...)` | `Booking` | event scenario: Tickets button |

The planner **must** produce actions backed by real tool results. A card that says "leave 30 min early" carries the ETA numbers that justify it. This is the difference from re-pushing the headline.

### 4.7 Channel behaviour (Telegram implementation)

- **Push:** Markdown message (headline / impact / detail) + `InlineKeyboardMarkup` from `card.actions`. `callback_data = f"{card.event_id}:{action.id}"`.
- **Button callback:** executes the action through the matching integration, edits the message to show the result ("✅ Reminder set for 8:25").
- **Follow-up:** any text reply while a card is the latest message → chat turn with the card + impact + tool results as context. Thread state in SQLite keyed by `(chat_id, event_id)`.
- Commands: `/start` (bind chat to profile), `/status`, `/demo <scenario>` (hidden).

Framework: `python-telegram-bot` (async), long polling.

### 4.8 Storage

SQLite via `sqlite3` stdlib: `seen_events`, `cards`, `threads`, `reminders`, `channel_messages` (message-id ↔ card-id). No ORM.

## 5. Hero scenarios (pre-built, rehearsed)

| # | Trigger | User context | Real tool calls | Card actions |
|---|---|---|---|---|
| 1 | I-580 crash (511 or inject) | 09:00 "Drop kids at school" | `route_eta` ×2 (with/without incident) | **Remind me at 8:25** · Show alternate route |
| 2 | Power outage tonight (inject) | 19:00 "Zoom — client call" | `find_places("cafe wifi", open_now)` | **Navigate to Blue Bottle** · See 3 options |
| 3 | Night market Saturday (Eventbrite) | Free Sat 17:00–22:00; likes live music | `free_slots`, `calendar_insert`, `checkout_url` | **Add to calendar** · Tickets |
| 4 (optional) | NWS heat/rain alert | Outdoor plan on calendar | `find_places("indoor …")` | Suggest indoor alternative |

Scenario 4 is the cheapest to run on **live** data (NWS is keyless) and is the fallback if race-day integration of 511 slips.

## 6. Agent framework

**PydanticAI** on top of DeepSeek's OpenAI-compatible endpoint.

- Typed tools and structured outputs map 1:1 onto the models in §4.1 and the Protocols in §4.3.
- Provider is one config line; if DeepSeek tool-calling misbehaves during rehearsal, switch to another provider without touching agent code.
- Fallback if PydanticAI fights us: hand-written tool loop on the `openai` SDK (~80 lines).

**DeepSeek Harness (dsh) — not used.** It is a Node.js coding-agent harness in developer preview (Aug 2026); our workload is a long-running poll→judge→push service, and the agent loop is small enough that a preview framework adds risk without capability.

## 7. Tooling and keys

```
Python 3.12, uv
pydantic-ai, python-telegram-bot, apscheduler, httpx, feedparser, pyyaml
google-api-python-client + google-auth-oauthlib  (Calendar)
pytest
```

`.env`:
```
DEEPSEEK_API_KEY=
TELEGRAM_BOT_TOKEN=
GOOGLE_MAPS_API_KEY=          # Routes + Places
BAY511_TOKEN=
EVENTBRITE_TOKEN=             # or TICKETMASTER_KEY
GOOGLE_OAUTH_CLIENT_JSON=     # Calendar; optional, mock fallback
DEMO_MODE=1                   # mute real feeds except allowlist
```

## 8. Error handling and demo safety

- Any sensor failure: log, skip that poll. Never crash the loop.
- Any integration failure: the tool returns an error object; the planner omits that detail rather than inventing it.
- LLM failure or low confidence: **no push**. Silence beats a wrong card in front of judges.
- Tool failure inside the planner: card still sent with the actions that succeeded.
- Dedupe by `event.id`; push rate cap (default 3/hour) so live feeds cannot spam during the demo.
- `DEMO_MODE=1`: real sensors run but only events matching an allowlist (NWS + injector) reach the bot.
- Scenario JSONs pinned to **relative** times (`"starts_at": "+45m"`) so they replay correctly at any hour.
- `calendar: mock` is the race-day fallback if Google OAuth misbehaves; same interface, no other change.

## 9. Stretch: god-view page

FastAPI + SSE + one HTML page on the projector: a live log of `event received → prefilter pass → LLM: affected (why) → tool calls → card pushed`. Makes the pipeline visible while judges watch the phone. Build only if all three hero scenarios are green by Friday.

## 10. Testing

- `pytest` on prefilter rules (pure functions: geo, time, type gate).
- Protocol conformance: each integration provider passes the same small test suite against its Protocol (Mock and Google Calendar run the same tests).
- Scenario replay test: inject each `scenarios/*.json` through the pipeline, assert a `Card` is produced with the expected `action.kind`s (LLM live; mark `@pytest.mark.llm`).
- Manual rehearsal checklist (race day): each scenario × push → button → follow-up, timed.

Run: `uv run pytest -m "not llm"` (fast) / `uv run pytest` (full).

## 11. Timeline

### Pre-build (before Saturday)

| Day | Dev A — agent brain | Dev B — sensors & integrations |
|---|---|---|
| 1 | Models (§4.1), relevance prefilter + tests | Repo skeleton, `uv`, config + `integrations.yaml` registry, Protocols (§4.3), SQLite, Telegram `Channel` echo, injector, Mock calendar |
| 2 | Stage-2 relevance prompt, planner + tools on DeepSeek (against Mock calendar) | Google `Maps` (Routes + Places), NWS + 511 sensors, scheduler `Reminders` |
| 3 | Scenarios 1–3 end-to-end; card copy; follow-up chat | Card rendering + buttons + callbacks in Telegram; `Booking.open_url`; Eventbrite sensor |
| 4 | Prompt tuning on live NWS/511 noise (no false pushes) | Google `Calendar` OAuth; `DEMO_MODE`; full rehearsal ×2 |

Exit criterion for Friday night: all three hero scenarios run push → button → follow-up on a phone, twice in a row, without touching the terminal.

### Race day (4h)

| Time | Work |
|---|---|
| 0:00–1:30 | Wire one more live source or harden 511; verify zero false pushes on real feeds |
| 1:30–2:30 | Follow-up conversation polish; card copy; god-view if time |
| 2:30–3:30 | Full rehearsal ×3; fix what breaks; freeze |
| 3:30–4:00 | Pitch run-through |

## 12. Pitch outline (3 min)

1. **Problem** — NewsBreak tells you 580 is jammed. You still have to do the math.
2. **Heads Up** — News happens → does it affect me → what should I do. Show the two-layer diagram once: world-side sensors, user-side integrations, agent in the middle.
3. **Live demo** — `/demo 580` → card lands on the phone → tap *Remind me* → ask "what if I take 880?" → agent answers with ETA. Then the outage card, then the night market card.
4. **Why NewsBreak** — the moat is hyperlocal real-time context; no one else has the sensor. And it plugs into the tools people already use — calendar, maps, messenger — through one interface each.
5. **Business** — attention → ads becomes intent → transaction. Every button you just saw is a lead; `Booking` is where it clears.
6. **Next** — more sensors, more integrations (WhatsApp, Apple Calendar, OpenTable), more surfaces (in-app push, car, watch).

## 13. Out of scope

- Real NewsBreak data or scraping (fragile, not needed for the story).
- Multi-user / auth (single demo profile).
- Real PG&E / school-district feeds (injector).
- Second real provider for any integration (WhatsApp, Apple/Outlook calendar, Mapbox, real booking checkout) — interfaces exist, implementations do not.
- Native app, voice.
- Fine-tuning; retrieval over news archives.
