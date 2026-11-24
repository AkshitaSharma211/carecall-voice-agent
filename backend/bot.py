import os
import datetime
from typing import Optional
import certifi
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
import aiohttp
from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineWorker
from pipecat.workers.runner import WorkerRunner
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.transports.base_transport import TransportParams
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.services.elevenlabs.stt import ElevenLabsSTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.llm_service import FunctionCallParams

import tools as t
from db import init_db

load_dotenv()
init_db()  # safe on every start: creates tables and seeds only if empty


def make_prompt() -> str:
    today = datetime.date.today().isoformat()
    return f"""You are a friendly receptionist for a clinic. Today is {today}.
Your replies are spoken aloud: short sentences, no lists, no emojis.
You can check availability, book, and cancel appointments using your tools.
Rules:
- Identify the caller only by the phone number they say. Before booking or cancelling, read the number back digit by digit and wait for a clear yes.
- Only offer slots returned by the availability tool. Never invent slots. Never say slot ids aloud.
- Say dates and times naturally, for example "tomorrow at 11 AM".
- Convert dates the caller says (like "tomorrow") into YYYY-MM-DD before calling a tool.
- If a tool returns an error message, follow its instruction and tell the caller in plain words.
- After booking or cancelling, confirm the doctor, date and time.
- When you call a tool, pass the phone number as digits only, like +919876543210, converting spoken words such as "zero" into digits."""


# ---- tools: thin wrappers the LLM can call; the real logic lives in tools.py ----

async def check_doctor_availability(
    params: FunctionCallParams,
    speciality: Optional[str] = None,
    doctor_name: Optional[str] = None,
    date: Optional[str] = None,
):
    """Find free appointment slots.

    Args:
        speciality: Dermatology, Cardiology or General Physician.
        doctor_name: Doctor's name, only if the caller asked for one.
        date: Date as YYYY-MM-DD.
    """
    await params.result_callback(t.check_doctor_availability(speciality, doctor_name, date))


async def book_appointment(
    params: FunctionCallParams,
    slot_id: int,
    phone: str,
    patient_name: str = "Caller",
):
    """Book a slot for the caller.

    Args:
        slot_id: The slot_id from the availability results.
        phone: The phone number the caller said, confirmed by read-back.
        patient_name: The caller's name.
    """
    await params.result_callback(t.book_appointment(slot_id, phone, patient_name))


async def cancel_appointment(params: FunctionCallParams, phone: str):
    """Cancel the caller's appointment.

    Args:
        phone: The phone number the caller said, confirmed by read-back.
    """
    await params.result_callback(t.cancel_appointment(phone))


async def run_bot(transport, runner_args: RunnerArguments):
    session = aiohttp.ClientSession()  # ElevenLabs STT needs an HTTP session

    stt = ElevenLabsSTTService(
        api_key=os.getenv("ELEVENLABS_API_KEY"),
        aiohttp_session=session,
    )
    tts = ElevenLabsTTSService(
        api_key=os.getenv("ELEVENLABS_API_KEY"),
        settings=ElevenLabsTTSService.Settings(
            voice=os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
        ),
    )
    # Any OpenAI-compatible provider (Groq, Cerebras, OpenRouter): change only .env
    llm = OpenAILLMService(
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
        settings=OpenAILLMService.Settings(
            model=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
        ),
    )

    context = LLMContext(
        messages=[{"role": "system", "content": make_prompt()}],
        tools=[check_doctor_availability, book_appointment, cancel_appointment],
    )
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )

    pipeline = Pipeline([
        transport.input(),
        stt,
        user_aggregator,
        llm,
        tts,
        transport.output(),
        assistant_aggregator,
    ])

    worker = PipelineWorker(pipeline)
    runner = WorkerRunner(handle_sigint=runner_args.handle_sigint)
    await runner.add_workers(worker)

    @worker.rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        context.add_message(
            {"role": "user", "content": "Greet the caller briefly and ask how you can help."}
        )
        await worker.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        await runner.cancel()

    try:
        await runner.run()
    finally:
        await session.close()


async def bot(runner_args: RunnerArguments):
    transport_params = {
        "webrtc": lambda: TransportParams(audio_in_enabled=True, audio_out_enabled=True),
    }
    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()