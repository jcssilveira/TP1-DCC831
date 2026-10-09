import os, json, random
from collections import defaultdict, Counter
import numpy as np
from scipy.io.wavfile import write
import synthesize_audio

def train_markov(audio_dir, max_carts=None):
    models = {ch: defaultdict(Counter) for ch in range(1, 5)}
    carts = os.listdir(audio_dir)
    if max_carts:
        carts = carts[:max_carts]
    for cid in carts:
        path = os.path.join(audio_dir, cid, "audio.json")
        if not os.path.exists(path): continue
        with open(path) as f: data = json.load(f)
        sfx_map = {s["id"]: s for s in data.get("sfx", [])}
        
        for pat in data.get("music", []):
            for ch in range(1, 5):
                s_id = pat.get(f"ch{ch}", 64)
                if s_id < 64 and s_id in sfx_map:
                    notes = sfx_map[s_id].get("notes", [])
                    if len(notes) != 32: continue
                    t_notes = [(0, 0, 0, 0) if n["volume"] == 0 else (n["pitch"], n["instrument"], n["volume"], n["effect"]) for n in notes]
                    for i in range(len(t_notes) - 1):
                        models[ch][t_notes[i]][t_notes[i + 1]] += 1
    return models

def sample_next(counter, temp=1.0):
    if not counter: return (0, 0, 0, 0)
    items = list(counter.keys())
    weights = [c ** (1.0 / max(0.01, temp)) for c in counter.values()]
    return random.choices(items, weights=weights, k=1)[0]

def generate_sfx(model, sfx_id, speed=16, temp=1.0):
    sound_keys = [k for k in model.keys() if k[2] > 0]
    curr = random.choice(sound_keys) if sound_keys else (0, 0, 0, 0)
    notes = [curr]
    
    for _ in range(31):
        curr = sample_next(model.get(curr, {}), temp)
        # Se cair em pausa e tiver notas com som, 25% de chance de reativar para manter o ritmo
        if curr == (0, 0, 0, 0) and sound_keys and random.random() < 0.25:
            curr = random.choice(sound_keys)
        notes.append(curr)
        
    return {
        "id": sfx_id, "speed": speed, "loop_start": 0, "loop_end": 0,
        "notes": [{"pitch": p, "instrument": i, "volume": v, "effect": f} for p, i, v, f in notes]
    }

def compose_and_save(models, out_wav, num_patterns=6, speed=16, temp=1.0):
    all_sfx, music, sfx_id = [], [], 0
    for p in range(num_patterns):
        pat = {"id": p, "flags": 0}
        for ch in range(1, 5):
            all_sfx.append(generate_sfx(models[ch], sfx_id, speed, temp))
            pat[f"ch{ch}"] = sfx_id
            sfx_id += 1
        music.append(pat)

    waves = [synthesize_audio.mix_music_pattern(p, all_sfx) for p in music]
    full_song = np.concatenate([w for w in waves if w is not None and len(w) > 0])
    full_song = (full_song / np.max(np.abs(full_song))) * 0.92
    write(out_wav, synthesize_audio.SAMPLE_RATE, np.int16(full_song * 32767))
    print(f"Salvo: {out_wav}")

if __name__ == "__main__":
    os.makedirs("outputs", exist_ok=True)
    print("Treinando modelo sobre todos os cartuchos...")
    models = train_markov("data/audio")
    
    for tau, name in [(0.6, "simples_tau_0_6.wav"), (1.0, "simples_tau_1_0.wav"), (1.6, "simples_tau_1_6.wav")]:
        compose_and_save(models, f"outputs/{name}", temp=tau)
