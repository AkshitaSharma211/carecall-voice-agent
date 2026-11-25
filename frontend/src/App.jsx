import { useEffect, useRef, useState } from "react";
import { PipecatClient } from "@pipecat-ai/client-js";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";
import "./App.css";

const get = (p) => fetch(`/data/${p}`).then((r) => r.json());
const fmt = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

function beep(freq, ms, when = 0) {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.frequency.value = freq; g.gain.value = 0.05;
    o.connect(g); g.connect(ctx.destination);
    o.start(ctx.currentTime + when); o.stop(ctx.currentTime + when + ms / 1000);
    setTimeout(() => ctx.close(), when * 1000 + ms + 200);
  } catch {}
}

function Wave({ stream }) {
  const ref = useRef(null);
  useEffect(() => {
    const cv = ref.current, g = cv.getContext("2d");
    const data = new Uint8Array(32);
    let raf, ctx, an;
    if (stream) {
      ctx = new AudioContext();
      an = ctx.createAnalyser(); an.fftSize = 64;
      ctx.createMediaStreamSource(stream).connect(an);
    }
    const draw = () => {
      g.clearRect(0, 0, cv.width, cv.height);
      if (an) an.getByteFrequencyData(data);
      g.fillStyle = "#1f4d3a";
      for (let i = 0; i < 24; i++) {
        const h = 4 + (data[i] / 255) * 56;
        g.fillRect(i * 11 + 2, (cv.height - h) / 2, 6, h);
      }
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => { cancelAnimationFrame(raf); if (ctx) ctx.close(); };
  }, [stream]);
  return <canvas ref={ref} width={270} height={64} />;
}

export default function App() {
  const [phase, setPhase] = useState("idle"); // idle | ringing | live | ended
  const [lines, setLines] = useState([]);
  const [muted, setMuted] = useState(false);
  const [secs, setSecs] = useState(0);
  const [botStream, setBotStream] = useState(null);
  const [card, setCard] = useState(null);
  const [doctors, setDoctors] = useState([]);
  const [slots, setSlots] = useState([]);
  const [appts, setAppts] = useState([]);
  const [flash, setFlash] = useState({});
  const client = useRef(null), audio = useRef(null), prev = useRef(null);
  const ring = useRef(null), box = useRef(null);
  const phaseRef = useRef(phase); phaseRef.current = phase;

  const refresh = async () => {
    const [d, s, a] = await Promise.all([get("doctors"), get("slots"), get("appointments")]);
    setDoctors(d); setSlots(s); setAppts(a);
    const changed = {};
    if (prev.current) for (const x of a) {
      if (prev.current[x.id] !== x.status) {
        changed[x.id] = true;
        if (phaseRef.current === "live") { setCard(x); setTimeout(() => setCard(null), 7000); }
      }
    }
    prev.current = Object.fromEntries(a.map((x) => [x.id, x.status]));
    if (Object.keys(changed).length) { setFlash(changed); setTimeout(() => setFlash({}), 2000); }
  };

  useEffect(() => { refresh(); }, []);
  useEffect(() => {
    if (phase !== "live") return;
    const poll = setInterval(refresh, 1500);
    const tick = setInterval(() => setSecs((s) => s + 1), 1000);
    return () => { clearInterval(poll); clearInterval(tick); };
  }, [phase]);
  useEffect(() => { if (box.current) box.current.scrollTop = box.current.scrollHeight; }, [lines]);

  const add = (who, text) => setLines((l) => [...l, { who, text }]);
  const finish = () => {
    clearInterval(ring.current);
    if (phaseRef.current === "idle" || phaseRef.current === "ended") return;
    beep(300, 350); setPhase("ended"); setBotStream(null); refresh();
  };

      const attachBot = (track) => {
    if (!track || !audio.current) return;
    const cur = audio.current.srcObject;
    if (cur && cur.getAudioTracks().includes(track)) return;
    const st = new MediaStream([track]);
    audio.current.srcObject = st;
    audio.current.muted = false;
    audio.current.play().catch(() => {
      const resume = () => { audio.current.play(); window.removeEventListener("click", resume); };
      window.addEventListener("click", resume);
    });
    setBotStream(st);
  };

  const grab = () => attachBot(client.current?.tracks?.()?.bot?.audio);

  const start = async () => {
    setLines([]); setSecs(0); setMuted(false); setCard(null); setPhase("ringing");
    beep(440, 400); beep(480, 400, 0.5);   // one short ring, no loop
    const c = new PipecatClient({
      transport: new SmallWebRTCTransport(),
      enableMic: true,
      enableCam: false,
      callbacks: {
        onConnected: () => setPhase("live"),
        onDisconnected: finish,
        onUserTranscript: (d) => { if (d.final) add("you", d.text); },
        onBotTranscript: (d) => add("agent", d.text),
        onTrackStarted: (track, p) => {
          if (track.kind === "audio" && !(p && p.local)) attachBot(track);
        },
        onBotReady: grab,
        onBotStartedSpeaking: grab,
      },
    });
    client.current = c;
    try { await c.connect({ webrtcRequestParams: { endpoint: "/api/offer" } }); }
    catch (e) { console.error(e); setPhase("idle"); }
  };
      

  
  

  const end = async () => { await client.current?.disconnect(); finish(); };
  const mute = () => { client.current?.enableMic(muted); setMuted(!muted); };

  return (
    <main>
      <audio ref={audio} autoPlay />
      <section className="phone">
        <div className="screen" key={phase}>
          {phase === "idle" && (<div className="center">
            <h1>CareCall</h1>
            <p className="muted">Book or cancel an appointment by voice.</p>
            <button className="go" onClick={start}>Try Call</button>
          </div>)}
          {phase === "ringing" && (<div className="center">
            <div className="pulse" /><h2>CareCall</h2>
            <p className="muted">Calling…</p>
            <button className="stop" onClick={end}>Cancel</button>
          </div>)}
          {phase === "live" && (<>
            <div className="top"><strong>CareCall</strong><span className="muted">{fmt(secs)}</span></div>
            <Wave stream={botStream} />
            <div className="transcript" ref={box}>
              {lines.length === 0 && <span className="muted">Listening…</span>}
              {lines.map((l, i) => <p key={i}><b>{l.who}</b>{l.text}</p>)}
            </div>
            {card && (<div className="card">
              <b>{card.status === "booked" ? "Booked" : "Cancelled"}</b>
              <span>{card.doctor}</span>
              <span>{card.date.slice(5)} · {card.time}</span>
            </div>)}
            <div className="controls">
              <button className={`round ${muted ? "on" : ""}`} onClick={mute}>{muted ? "Unmute" : "Mute"}</button>
              <button className="round stop" onClick={end}>End</button>
            </div>
          </>)}
          {phase === "ended" && (<div className="center">
            <h2>Call ended</h2>
            <p className="muted">{fmt(secs)}</p>
            <button className="go" onClick={start}>Call again</button>
          </div>)}
        </div>
      </section>

      <section className="data">
        <h2>Doctors</h2>
        {doctors.map((d) => (
          <div className="doctor" key={d.id}>
            <div><strong>{d.name}</strong> <span className="muted">{d.speciality}</span></div>
            <div className="chips">
              {slots.filter((s) => s.doctor === d.name).slice(0, 8).map((s) => (
                <span className="chip" key={s.slot_id}>{s.date.slice(5)} · {s.time}</span>
              ))}
            </div>
          </div>
        ))}
        <h2>Appointments</h2>
        {appts.length === 0 && <span className="muted">None yet</span>}
        {appts.map((a) => (
          <div className={`row ${a.status} ${flash[a.id] ? "flash" : ""}`} key={a.id}>
            <span>{a.date.slice(5)} · {a.time}</span>
            <span>{a.doctor}</span>
            <span className="muted">{a.phone}</span>
            <span className="tag">{a.status}</span>
          </div>
        ))}
      </section>
    </main>
  );
}
