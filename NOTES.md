# Interview notes

## `backend/bot.py`
WHAT: Configures the Pipecat voice pipeline, its clinic tools, prompts, and browser WebRTC transport.
WHY: Keeps speech recognition, tool use, and spoken replies in the existing Pipecat pipeline while making the Gemini model selectable through configuration.
ALTERNATIVE REJECTED: Replacing the pipeline with a mock or moving appointment rules out of `backend/tools.py`.

## `.env.example`
WHAT: Lists the environment variable names needed for local credentials and voice configuration, without values.
WHY: Lets a reviewer see required settings without exposing the local `.env` secrets.
ALTERNATIVE REJECTED: Checking in real credentials or including placeholder-looking secrets.

## `.gitignore`
WHAT: Excludes local credentials, databases, Python bytecode/environments, node dependencies, and run logs.
WHY: Keeps machine-specific and sensitive runtime files out of commits.
ALTERNATIVE REJECTED: Relying on manual staging discipline for generated files and credentials.
