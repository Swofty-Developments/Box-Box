"""
Race state built from telemetry frames: lap history, stints, the race log, and the triggers
that ask the engineer for a strategy call (every completed lap, and immediately on events).
"""
from dataclasses import dataclass, field

RACE_SESSIONS = ("RACE", "UNKNOWN")
NEUTRALISED = ("FULL", "VIRTUAL")
WET_WEATHER = ("LIGHTRAIN", "HEAVYRAIN", "STORM")
WET_TYRES = ("INTER", "WET")
OUT_STATUSES = ("RETIRED", "DNF", "DSQ", "NOT_CLASSIFIED")

# A rival within this many places or seconds of the player is worth an immediate call when it stops
RIVAL_PLACES = 2
RIVAL_GAP_S = 4.0
# Damage increases (percent) that need an immediate call
WING_DAMAGE_STEP = 15
BODY_DAMAGE_STEP = 20
PUNCTURE_DAMAGE = 50
# Forecast rain that is worth warning about: this likely, this soon
FORECAST_RAIN_PCT = 40
FORECAST_WINDOW_MIN = 10


@dataclass
class Trigger:
    code: str
    detail: str
    urgent: bool = True


@dataclass
class LapRecord:
    lap: int
    time: float
    compound: str
    visual: str
    tyre_age: int
    position: int
    pit: bool
    neutralised: bool
    wet: bool
    wear: float | None


@dataclass
class Stint:
    compound: str
    visual: str
    start_lap: int
    end_lap: int | None = None


@dataclass
class CarHistory:
    idx: int
    name: str = ""
    laps: dict = field(default_factory=dict)
    stints: list = field(default_factory=list)
    pit_laps: list = field(default_factory=list)
    current_lap: int = 0
    stops: int = 0
    pit_status: str = "NONE"
    result_status: str = "ACTIVE"
    entry_position: int = 0
    entry_gap: float = 0.0
    pitted_this_lap: bool = False
    neutralised_this_lap: bool = False
    wet_this_lap: bool = False

    def lap_list(self) -> list:
        return [self.laps[k] for k in sorted(self.laps)]

    def last_lap(self):
        return self.laps[max(self.laps)] if self.laps else None

    def current_stint(self):
        return self.stints[-1] if self.stints else None

    def compounds_used(self) -> list:
        seen = []
        for s in self.stints:
            if s.visual and s.visual not in seen:
                seen.append(s.visual)
        return seen


def _avg_wear(car: dict) -> float | None:
    wear = car.get("tireWear") or {}
    values = [v for v in wear.values() if isinstance(v, (int, float))]
    return round(sum(values) / len(values), 1) if values else None


class RaceState:
    def __init__(self):
        self.reset("")

    def reset(self, session_uid: str):
        self.session_uid = session_uid
        self.frame = {}
        self.track = {}
        self.cars = []
        self.player_idx = -1
        self.lap = 0
        self.histories = {}
        self.log = []
        self.safety_car = "NONE"
        self.weather = ""
        self.rain_warned = False
        self.player_damage = {"wing": 0, "body": 0, "tyre": 0}
        self.player_penalties = 0
        self.started = False
        self.finished = False

    def is_race(self) -> bool:
        return (self.track.get("sessionType") or "UNKNOWN") in RACE_SESSIONS

    def player(self) -> dict | None:
        return next((c for c in self.cars if c.get("idx") == self.player_idx), None)

    def teammate(self) -> dict | None:
        player = self.player()
        team = player.get("teamId") if player else None
        if team in (None, 255):
            return None
        return next((c for c in self.cars if c.get("idx") != self.player_idx and c.get("teamId") == team), None)

    def player_history(self):
        return self.histories.get(self.player_idx)

    def total_laps(self) -> int:
        return int(self.track.get("totalLaps") or 0)

    def laps_remaining(self) -> int | None:
        total = self.total_laps()
        return max(0, total - self.lap + 1) if total and self.lap else None

    def is_wet(self) -> bool:
        return (self.track.get("weather") or "").upper() in WET_WEATHER

    def _new_session(self, frame: dict) -> bool:
        uid = str(frame.get("sessionUid") or "")
        if uid and uid != self.session_uid:
            return True
        track = frame.get("track") or {}
        if self.track and track.get("id") != self.track.get("id"):
            return True
        return bool(self.lap) and (frame.get("lap") or 0) < self.lap - 1

    def _log(self, text: str):
        self.log.append({"lap": self.lap, "text": text})

    def name(self, idx: int) -> str:
        h = self.histories.get(idx)
        return h.name if h and h.name else f"#{idx}"

    def update(self, frame: dict) -> tuple[list, bool]:
        """Absorb one frame; return the triggers it raised and whether a new session began."""
        new_session = self._new_session(frame)
        if new_session:
            self.reset(str(frame.get("sessionUid") or ""))
        was_finished = self.finished
        self.frame = frame
        self.track = frame.get("track") or {}
        self.cars = frame.get("cars") or []
        self.player_idx = frame.get("player_idx", -1)
        self.lap = frame.get("lap") or 0

        triggers = []
        self._update_safety_car(triggers)
        self._update_weather(triggers)
        for event in frame.get("events") or []:
            self._handle_event(event, triggers)
        for car in self.cars:
            self._update_car(car, triggers)
        self._update_player(triggers)

        if not self.is_race() or was_finished:
            return [], new_session
        if not self.started and self.lap >= 1 and self.player():
            self.started = True
            triggers.insert(0, Trigger("RACE_START", f"lap {self.lap} of {self.total_laps() or '?'}"))
        return triggers, new_session

    def _update_safety_car(self, triggers: list):
        sc = self.track.get("safetyCar") or "NONE"
        if sc == self.safety_car:
            return
        if sc in NEUTRALISED:
            label = "SAFETY CAR" if sc == "FULL" else "VIRTUAL SAFETY CAR"
            self._log(f"{label} deployed")
            triggers.append(Trigger("SAFETY_CAR", f"{label} deployed"))
        elif self.safety_car in NEUTRALISED:
            self._log("Green flag, racing resumed")
            triggers.append(Trigger("GREEN_FLAG", "safety car period over, racing resumed"))
        self.safety_car = sc

    def _update_weather(self, triggers: list):
        weather = self.track.get("weather") or ""
        was_wet = self.weather.upper() in WET_WEATHER
        now_wet = weather.upper() in WET_WEATHER
        if self.weather and weather != self.weather:
            self._log(f"Weather {self.weather} -> {weather}")
            if now_wet != was_wet:
                code = "RAIN" if now_wet else "DRYING"
                triggers.append(Trigger(code, f"weather now {weather}"))
        self.weather = weather

        soon = [s for s in self.track.get("rainForecast") or [] if s.get("minutes", 99) <= FORECAST_WINDOW_MIN]
        rain_coming = any((s.get("rain") or 0) >= FORECAST_RAIN_PCT for s in soon)
        if rain_coming and not self.rain_warned and not now_wet:
            peak = max(soon, key=lambda s: s.get("rain") or 0)
            self._log(f"Forecast: {peak['rain']}% rain in {peak['minutes']} min")
            triggers.append(Trigger("RAIN_FORECAST", f"{peak['rain']}% chance of rain in {peak['minutes']} min"))
        self.rain_warned = rain_coming

    def _handle_event(self, event: dict, triggers: list):
        code = event.get("code")
        car = event.get("car", -1)
        detail = event.get("detail") or ""
        if code == "SAFETY_CAR" and "RETURNING" in detail:
            self._log("Safety car in this lap")
            triggers.append(Trigger("SAFETY_CAR_ENDING", "safety car comes in at the end of this lap"))
        elif code == "RED_FLAG":
            self._log("RED FLAG")
            triggers.append(Trigger("RED_FLAG", "session red-flagged"))
        elif code == "RETIREMENT":
            self._log(f"{self.name(car)} retired {detail}".strip())
            triggers.append(Trigger("RETIREMENT", f"{self.name(car)} retired, watch for a safety car"))
        elif code == "PENALTY":
            self._log(f"Penalty {self.name(car)}: {detail}")
            if car == self.player_idx:
                triggers.append(Trigger("PENALTY", detail))
        elif code == "COLLISION" and car == self.player_idx:
            self._log(f"Contact {detail}")
            triggers.append(Trigger("CONTACT", f"contact {detail}, check for damage"))
        elif code == "CHEQUERED_FLAG":
            self._log("Chequered flag")

    def _update_car(self, car: dict, triggers: list):
        idx = car.get("idx")
        h = self.histories.get(idx)
        if h is None:
            h = self.histories[idx] = CarHistory(idx=idx, current_lap=car.get("currentLap") or 0)
        h.name = car.get("name") or h.name
        compound = car.get("compound") or ""
        visual = car.get("visualCompound") or compound

        if not h.stints:
            h.stints.append(Stint(compound, visual, max(1, h.current_lap)))

        # Close the previous lap with what earlier frames saw, before this frame marks the new lap
        current_lap = car.get("currentLap") or 0
        if current_lap > h.current_lap:
            if h.current_lap >= 1:
                h.laps[h.current_lap] = LapRecord(
                    lap=h.current_lap,
                    time=float(car.get("lastLapTime") or 0.0),
                    compound=compound,
                    visual=visual,
                    tyre_age=int(car.get("tyreAge") or car.get("stintLaps") or 0),
                    position=car.get("position") or 0,
                    pit=h.pitted_this_lap,
                    neutralised=h.neutralised_this_lap,
                    wet=h.wet_this_lap,
                    wear=_avg_wear(car),
                )
                if idx == self.player_idx and self.is_race():
                    triggers.append(Trigger("LAP", f"lap {h.current_lap} complete", urgent=False))
            h.current_lap = current_lap
            h.pitted_this_lap = h.neutralised_this_lap = h.wet_this_lap = False

        if self.safety_car in NEUTRALISED:
            h.neutralised_this_lap = True
        if self.is_wet():
            h.wet_this_lap = True

        pit_status = car.get("pitStatus") or "NONE"
        if pit_status != "NONE":
            h.pitted_this_lap = True
        if h.pit_status == "NONE" and pit_status != "NONE":
            h.entry_position = car.get("position") or 0
            h.entry_gap = car.get("gapToLeader") or 0.0
            self._teammate_entered_pits(car, triggers)
        stops = car.get("numPitStops") or 0
        if stops > h.stops:
            h.stops = stops
            h.pit_laps.append(car.get("currentLap") or self.lap)
        if h.pit_status != "NONE" and pit_status == "NONE":
            self._car_left_pits(car, h, triggers)
        elif not h.stints[-1].compound and compound:
            h.stints[-1].compound, h.stints[-1].visual = compound, visual
        h.pit_status = pit_status

        status = car.get("resultStatus") or "ACTIVE"
        if status != h.result_status and status in OUT_STATUSES and idx != self.player_idx:
            self._log(f"{h.name} out of the race ({status})")
        h.result_status = status


    def _teammate_entered_pits(self, car: dict, triggers: list):
        mate = self.teammate()
        player = self.player()
        if not mate or mate.get("idx") != car.get("idx") or not player or not self.is_race():
            return
        behind_by = (player.get("gapToLeader") or 0.0) - (car.get("gapToLeader") or 0.0)
        where = f"{behind_by:.1f}s ahead of you" if behind_by >= 0 else f"{-behind_by:.1f}s behind you"
        self._log(f"Teammate {car.get('name')} entering the pits from P{car.get('position')}")
        triggers.append(Trigger(
            "TEAMMATE_PIT",
            f"teammate {car.get('name')} is entering the pits now from P{car.get('position')}, {where}",
        ))

    def _car_left_pits(self, car: dict, h: CarHistory, triggers: list):
        lap = car.get("currentLap") or self.lap
        compound = car.get("compound") or ""
        visual = car.get("visualCompound") or compound
        if h.stints:
            h.stints[-1].end_lap = lap
        h.stints.append(Stint(compound, visual, lap))
        label = f"{visual} ({compound})" if visual and visual != compound else compound
        self._log(f"{h.name} pitted, rejoined P{car.get('position')} on {label}")
        mate = self.teammate()
        if car.get("idx") == self.player_idx or (mate and mate.get("idx") == car.get("idx")):
            return
        player = self.player()
        if not player or not self.is_race():
            return
        player_pos = player.get("position") or 99
        place_gap = abs(h.entry_position - player_pos)
        time_gap = abs(h.entry_gap - (player.get("gapToLeader") or 0.0))
        if place_gap <= RIVAL_PLACES or time_gap <= RIVAL_GAP_S:
            was = "ahead of" if h.entry_position < player_pos else "behind"
            now = "ahead of" if (car.get("position") or 99) < player_pos else "behind"
            # Only the cars either side under green flag need a call now; the rest wait for the lap call
            urgent = place_gap <= 1 and self.safety_car not in NEUTRALISED
            triggers.append(Trigger(
                "RIVAL_PIT",
                f"{h.name} (was P{h.entry_position}, {was} you) pitted for {label}, "
                f"rejoined P{car.get('position')} {now} you",
                urgent=urgent,
            ))

    def _update_player(self, triggers: list):
        player = self.player()
        if not player:
            return
        wing = player.get("damage") or 0
        body = player.get("bodyDamage") or 0
        tyre = player.get("tyreDamage") or 0
        base = self.player_damage
        if tyre >= PUNCTURE_DAMAGE > base["tyre"]:
            self._log(f"PLAYER tyre damage {tyre}%")
            triggers.append(Trigger("PUNCTURE", f"tyre damage {tyre}%"))
        if wing - base["wing"] >= WING_DAMAGE_STEP:
            self._log(f"PLAYER front wing damage {wing}%")
            triggers.append(Trigger("DAMAGE", f"front wing damage {wing}%"))
            base["wing"] = wing
        if body - base["body"] >= BODY_DAMAGE_STEP:
            self._log(f"PLAYER body damage {body}%")
            triggers.append(Trigger("DAMAGE", f"floor/body damage {body}%"))
            base["body"] = body
        base["tyre"] = tyre
        base["wing"] = min(base["wing"], wing)
        base["body"] = min(base["body"], body)

        penalties = player.get("penaltiesSec") or 0
        if penalties > self.player_penalties:
            self._log(f"PLAYER penalty now {penalties}s")
            triggers.append(Trigger("PENALTY", f"time penalties now {penalties}s", urgent=False))
        self.player_penalties = penalties

        if (player.get("resultStatus") or "ACTIVE") == "FINISHED" and not self.finished and self.started:
            self.finished = True
            self._log(f"Finished P{player.get('position')}")
            triggers.append(Trigger("FINISH", f"finished P{player.get('position')}"))
