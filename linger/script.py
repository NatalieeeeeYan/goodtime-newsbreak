from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

BOT_NAME = "LingerBot"
TZ = ZoneInfo("America/Los_Angeles")

# Group members played by separate bots (name -> env var holding that bot's token).
MEMBER_BOTS = {
    "Andrew": "ANDREW_BOT_TOKEN",
    "Brandon": "BRANDON_BOT_TOKEN",
    "Christopher": "CHRISTOPHER_BOT_TOKEN",
}
PRESENTER = "Joshua"


def hangout_date(today: date | None = None) -> date:
    today = today or datetime.now(TZ).date()
    return today + timedelta(days=(5 - today.weekday()) % 7)


def hangout_date_label() -> str:
    d = hangout_date()
    return f"Saturday, {d.strftime('%b')} {d.day}"


GROUP_CHATTER = [
    ("Andrew", "is anyone around saturday? i have zero plans and i refuse to do laundry again"),
    ("Brandon", "i can do after 2, Ravi has soccer till 1:30"),
    ("Christopher", "free all afternoon, i can drive"),
]

CHECKING = "⏳ Checking 4 calendars… 🔒 free/busy only, I can't see what your events are."
CHECKED = "✅ Checked 4 calendars 🔒 free/busy only, I can't see what your events are."

CONSTRAINTS = """Everyone's free 1–6 PM except Brandon, who's free from 2. Here's what I'm working with:

<b>CONSTRAINTS</b>
👥 4 people · Saturday 1:00 – 6:00 PM
🥗 Andrew is vegetarian
🚲 Joshua has no car, bike or Caltrain
🅿️ Brandon needs easy parking
💵 Around $40 per person"""

PLANS_INTRO = "Three options. All start at 2:00 so Brandon doesn't miss anything."

PLANS = [
    {
        "key": "1",
        "title": "Board games + late lunch",
        "fit": 84,
        "meta": "3 hr 45 · ~$32/person",
        "arrivals": "Christopher 1:44 · Andrew 1:38 · Joshua 1:52 (bike) · Brandon 2:00",
        "signals": ["🏷️ 2-for-1 deal this weekend", "🎲 Joshua: board games", "🅿️ Garage C, 3 min walk"],
        "plan_b": "If Meeple House is packed, the back room at Foothill Taproom has the same shelf.",
    },
    {
        "key": "2",
        "title": "Art market + veg dinner",
        "fit": 91,
        "meta": "4 hr · ~$40/person",
        "arrivals": "Christopher 1:40 · Andrew 1:36 · Joshua 1:49 (bike) · Brandon 2:00, joins at 2:05",
        "signals": ["🎨 Art market today 12–5", "🥗 Andrew: vegetarian, Green Bowl", "🅿️ Garage A for Brandon"],
        "plan_b": "If rain moves up, market 2:00–3:15 then straight to Green Bowl.",
    },
    {
        "key": "3",
        "title": "Coffee crawl + Shoreline sunset",
        "fit": 76,
        "meta": "4 hr 15 · ~$26/person",
        "arrivals": "Christopher 1:41 · Andrew 1:37 · Joshua 1:50 (bike) · Brandon 2:00",
        "signals": ["📍 Neighbor post: last night's sunset", "🌧️ Rain at 4:30 makes this risky", "🅿️ Free lot at Shoreline"],
        "plan_b": "Rain makes this the shakiest of the three. That is why it ranked it last.",
    },
]

POLL_TITLE = "Which plan? Voting closes at 6 PM tonight."
POLL_OPTIONS = [
    ("1", "Plan 1 · Board games + late lunch"),
    ("2", "Plan 2 · Art market + veg dinner"),
    ("3", "Plan 3 · Coffee crawl + Shoreline"),
    ("x", "Can't make it"),
]
# Fake tallies from the other members, applied after the presenter votes.
POLL_OTHERS = {"2": ["Andrew", "Brandon"], "x": ["Christopher"]}

ANDREW_VOTE_MSG = "Plan 2 pls, I want to see the art market 🎨"

RESULT_INTRO = "Plan 2 wins (3 of 4) 🎉 Locking it in."
BOOKING_STEPS = [
    "⏳ Adding to 4 calendars…",
    "⏳ Booking Green Bowl, table for 4 at 4:30 PM…",
    "✅ Calendars updated · table booked",
]

RESULT_CARD = """<b>Art market + veg dinner</b>
{date} · 2:00 – 6:00 PM · Mountain View

✅ Added to everyone's calendar
✅ Table for 4 booked at Green Bowl, 4:30 PM (vegetarian-friendly)
🅿️ Suggested parking: Garage A, 3 min walk for Brandon
🚲 Joshua: 9 min by bike, staffed rack on Church St"""

EVENT_TITLE = "Art market + veg dinner"
EVENT_LOCATION = "Civic Center Plaza, Mountain View, CA"
EVENT_START = (14, 0)
EVENT_END = (18, 0)

MAPS_BIKE_URL = (
    "https://www.google.com/maps/dir/?api=1"
    "&origin=Church+St,+Mountain+View,+CA"
    "&destination=Civic+Center+Plaza,+Mountain+View,+CA"
    "&travelmode=bicycling"
)
MAPS_GARAGE_URL = "https://www.google.com/maps/search/?api=1&query=Parking+Garage+A,+Mountain+View,+CA"

DM_INTRO = "Hey Joshua, you're on for today. Plan 2: art market at Civic Center Plaza, then Green Bowl at 4:30."

DM_CARD = """<b>YOUR DEPARTURE</b>
<b>Leave at 1:49</b>

🚲 9 min by bike · 1.4 mi via Church St. No car needed today.
⚠️ Bike theft reports are up near the Caltrain lot this month. Use the staffed rack on Church St instead."""

DM_OUTRO = "Rain is possible after 4:30. I'll message you before you leave if it moves."

LIVE_UPDATE = """<i>Saturday, 1:00 PM</i>

Two things moved. Rain is now expected at 3:30, and NewsBreak just flagged a concert at the Civic Center amphitheater tonight — doors at 3, right next to Garage A, so it'll fill early. I suggest the market at 2:00–3:15 and Garage C for Brandon instead. OK?

🌧️ Rain moved up to 3:30 · 🎸 <b>EVENT</b> 0.2 mi · Concert at Civic Center, doors 3 PM · <i>NewsBreak Events · 1h</i>"""

LIVE_STEPS = [
    "⏳ Updating 4 calendars…",
    "⏳ Moving Green Bowl to 4:00 PM…",
    "✅ Updated calendars and the reservation. Green Bowl is now 4:00.",
]
LIVE_KEPT = "Keeping the original plan. I'll ping again if the rain moves earlier."

FEEDBACK_INTRO = """<i>Sunday, 10:00 AM</i>

<b>How was yesterday?</b>
Tap per stop. It only takes a second."""
FEEDBACK_STOPS = [
    ("market", "Open-air art market"),
    ("coffee", "Driftwood Coffee"),
    ("dinner", "Green Bowl dinner"),
]
ANDREW_FEEDBACK = [("market", "up"), ("dinner", "up")]
FEEDBACK_LEARNED = "🧠 I'll remember Andrew loved the art market 🎨 and weight outdoor culture higher for Andrew next time."

ACKS = {
    "edit": "Sure — tell me what to change and I'll redo the constraints.",
    "change": "What should I change? Time, place or people.",
}

RESET_DONE = "Demo reset."
