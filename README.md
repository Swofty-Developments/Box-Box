# Box-Box World's First AI F1 Race Engineer

Box-Box is an AI-powered race engineer for home sim racing. It captures real-time telemetry, analyzes vehicle performance and race conditions, and turns them into contextual strategy recommendations. Telemetry processing, AI reasoning, and conversational voice output form a continuous loop between the virtual race engineer and the driver, bringing human-AI collaboration closer to a real motorsport engineering experience.

## What it does

- Listens for live **F1 24** and **F1 25** UDP telemetry and **Gran Turismo 7** JSON telemetry.
- Models tires, fuel, ERS, weather, and nearby opponents before the strategy call.
- Asks DeepSeek or Cerebras for pit-wall advice on a timed interval and speaks it with ElevenLabs.
- Lets the driver talk back on pit radio. The engineer answers in text and voice.
- Shows a live dashboard: standings, track map, selected-car data, and the radio log.
- Falls back to a 22-car simulator when a game is not connected.

## Run it

Python 3.10 or newer.

```bat
python -m venv venv
venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```

Put your AI provider key (DeepSeek or Cerebras) and your ElevenLabs key in `.env`, then start the server and the simulator:

```bat
start.bat
```

On PowerShell, use `.\start.ps1`. The dashboard opens at http://127.0.0.1:8000.

To run the pieces yourself:

```bat
venv\Scripts\python.exe server.py
venv\Scripts\python.exe simulator.py
```

## Connect F1 24 or F1 25

In the game, open Settings → Telemetry:

- UDP Telemetry: On
- UDP Broadcast / IP: this PC's LAN address, on the same network as the console
- UDP Port: `20777`
- UDP Send Rate: 20Hz or higher
- UDP Format (F1 25): `2025` or `2024`

Enter a session on track. The menus only send event packets. Box-Box reads the format from each packet's header. Set `F1_UDP_FORMAT` to `2024` or `2025` to force one layout. Gran Turismo 7 telemetry is accepted as JSON on UDP port `33740`.

## Pit radio

Click **MIC** or press Space to talk. Ask about tires, the pit window, gaps, or fuel. The reply is played through the page.

## Configuration

Copy `.env.example` to `.env`.

| Variable | Purpose |
| --- | --- |
| `AI_PROVIDER` | `deepseek` or `cerebras`. Defaults to `deepseek` |
| `DEEPSEEK_API_KEY` | DeepSeek API key |
| `DEEPSEEK_MODEL` | DeepSeek model. Defaults to `deepseek-v4-flash` |
| `DEEPSEEK_THINKING` | `enabled` or `disabled`. Unset uses the API default, which thinks |
| `DEEPSEEK_BASE_URL` | OpenAI-compatible API base URL. Defaults to `https://api.deepseek.com` |
| `CEREBRAS_API_KEY` | Cerebras API key |
| `CEREBRAS_MODEL` | Cerebras model. Defaults to `qwen-3.8-27b` |
| `CEREBRAS_REASONING_EFFORT` | `none`, `low`, `medium` or `high`. Defaults to `none`; `gpt-oss-120b` needs `low` or higher |
| `ELEVENLABS_API_KEY` | ElevenLabs key used for pit-radio voice |
| `ELEVENLABS_VOICE_ID` | Spoken voice. A default is used when this is empty |
| `ELEVENLABS_MODEL_ID` | Speech model. Defaults to `eleven_flash_v2_5` |
| `F1_PORT` | F1 UDP port. Defaults to `20777` |
| `F1_UDP_FORMAT` | `auto`, or a registered format: `2024` (F1 24), `2025` (F1 25). Defaults to `auto` |
| `GT7_PORT` | GT7 UDP port. Defaults to `33740` |
| `ANALYSIS_INTERVAL` | Seconds between strategy updates. Defaults to `15` |

## Layout

| File | Role |
| --- | --- |
| `server.py` | FastAPI app, UDP listeners, dashboard, and radio API |
| `f1/parser.py` | F1 UDP packet parser for all 22 cars |
| `f1/f1_24/`, `f1/f1_25/` | Per-game packet layouts, track ids, and compound ids |
| `providers/base.py` | OpenAI-compatible chat call shared by every provider |
| `providers/deepseek/`, `providers/cerebras/` | AI providers |
| `registry.py` | Name registry the F1 formats and AI providers register into |
| `engine_models.py` | Tire, fuel, weather, and opponent models |
| `analyzer.py` | Strategy and radio replies |
| `tts_bridge.py` | ElevenLabs speech |
| `simulator.py` | WebSocket telemetry source for local runs |
| `static/index.html` | Live dashboard |
