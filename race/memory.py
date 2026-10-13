"""
The engineer's memory of the current race: every call and radio exchange, the plan in force,
private notes, and what the driver has said about how they want to race.
"""


class EngineerMemory:
    def __init__(self):
        self.reset_race()

    def reset_race(self):
        self.calls = []
        self.radio = []
        self.notes = []
        self.preferences = []
        self.plan = None
        self.plan_lap = 0

    def add_preference(self, text: str) -> bool:
        text = (text or "").strip()
        if not text or text in self.preferences:
            return False
        self.preferences.append(text)
        return True

    def record_call(self, lap: int, reasons: list, result: dict):
        plan = result.get("plan") or {}
        if plan and plan != self.plan:
            self.plan, self.plan_lap = plan, lap
        self.calls.append({
            "lap": lap,
            "reasons": [r.code for r in reasons],
            "voice": result.get("voice", ""),
            "box": bool(result.get("box_this_lap")),
            "plan": (plan or {}).get("summary", ""),
        })
        note = (result.get("note") or "").strip()
        if note:
            self.notes.append({"lap": lap, "text": note})

    def record_radio(self, lap: int, driver: str, engineer: str):
        self.radio.append({"lap": lap, "driver": driver, "engineer": engineer})

    def describe(self) -> str:
        lines = ["What the driver has told you this race: " + ("; ".join(self.preferences) if self.preferences else "nothing yet")]
        if self.plan:
            p = self.plan
            lines.append(
                f"Plan in force (set L{self.plan_lap}): {p.get('summary', '')} "
                f"[stops left {p.get('stops_remaining')}, next box L{p.get('next_pit_lap')} for {p.get('next_compound')}]"
            )
        else:
            lines.append("Plan in force: none yet")
        if self.calls:
            lines.append("Your previous calls:")
            for c in self.calls:
                said = f'said "{c["voice"]}"' if c["voice"] else "stayed quiet"
                box = " BOX CALLED" if c["box"] else ""
                lines.append(f"  L{c['lap']} [{','.join(c['reasons'])}] {said}{box} | plan: {c['plan']}")
        if self.radio:
            lines.append("Radio with the driver:")
            for r in self.radio:
                lines.append(f'  L{r["lap"]} driver: "{r["driver"]}" / you: "{r["engineer"]}"')
        if self.notes:
            lines.append("Your notes:")
            for n in self.notes:
                lines.append(f"  L{n['lap']}: {n['text']}")
        return "\n".join(lines)
