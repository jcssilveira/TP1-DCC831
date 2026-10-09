import os
import json
import numpy as np
from scipy.io.wavfile import write

# General audio synthesis settings
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
DEFAULT_AUDIO_DIR = os.path.join(PROJECT_ROOT, "dataset_pico8", "audio")
AUDIO_DIR = os.environ.get("PICO8_AUDIO_DIR", DEFAULT_AUDIO_DIR)
SAMPLE_RATE = 44100
FPS = 120.0 

def get_freq(pitch):
    """Converts PICO-8 pitch (0-63) to frequency in Hertz."""
    return 65.406 * (2 ** (pitch / 12.0))

def generate_waveform(phase_array, inst, amp_array):
    """Generates audio samples combining oscillator phase, instrument type, and envelope amplitude."""
    phase = phase_array % 1.0
    
    if inst == 0:   wave = np.sin(2 * np.pi * phase)
    elif inst == 1: wave = 2 * np.abs(2 * phase - 1) - 1
    elif inst == 2: wave = 2 * phase - 1
    elif inst == 3: wave = np.where(phase < 0.5, 1.0, -1.0)
    elif inst == 4: wave = np.where(phase < 0.25, 1.0, -1.0)
    elif inst == 5: wave = (2 * phase - 1) 
    elif inst == 6: wave = np.random.uniform(-1, 1, len(phase))
    elif inst == 7: wave = np.sin(2 * np.pi * phase)
    else:           wave = np.sin(2 * np.pi * phase)
        
    return wave * amp_array

def synth_sfx(sfx_data, all_sfx_list=None):
    """DSP synthesizer: renders notes, envelopes, continuous phase, and audio effects."""
    if not sfx_data: 
        return np.array([])
        
    speed = max(1, sfx_data.get("speed", 16))
    note_duration = speed / FPS
    num_samples = int(SAMPLE_RATE * note_duration)
    
    t = np.linspace(0, note_duration, num_samples, endpoint=False)
    audio_signal = []
    notes = sfx_data.get("notes", [])
    
    for i, note in enumerate(notes):
        pitch, inst = note["pitch"], note["instrument"]
        vol, effect = note["volume"], note["effect"]
        
        if vol == 0:
            audio_signal.append(np.zeros(num_samples))
            continue
            
        base_amp = (vol / 7.0) * 0.35 
        base_freq = get_freq(pitch)
        
        freq_array = np.full(num_samples, base_freq)
        amp_array = np.full(num_samples, base_amp)
        
        # Apply special modulation effects
        if effect == 1: 
            next_pitch = notes[i+1]["pitch"] if (i + 1 < len(notes) and notes[i+1]["volume"] > 0) else pitch
            freq_array = np.linspace(base_freq, get_freq(next_pitch), num_samples)
        elif effect == 2: 
            freq_array = base_freq * (1.0 + 0.03 * np.sin(2 * np.pi * 8.0 * t))
        elif effect == 3: 
            freq_array = base_freq * np.maximum(0, 1.0 - (t / note_duration))
        elif effect == 4: 
            amp_array = base_amp * (t / note_duration)
        elif effect == 5: 
            amp_array = base_amp * (1.0 - (t / note_duration))
        elif effect in [6, 7]: 
            arp_pitches = [notes[(i + j) % 32]["pitch"] for j in range(4)]
            samples_per_step = int(SAMPLE_RATE * ((2.0 if effect == 6 else 4.0) / FPS))
            if samples_per_step > 0:
                for s in range(num_samples):
                    freq_array[s] = get_freq(arp_pitches[(s // samples_per_step) % 4])

        if inst in [5, 7]:
            amp_array *= np.exp(-t * 15.0) 
            
        phase_array = np.cumsum(freq_array) / SAMPLE_RATE
        wave = generate_waveform(phase_array, inst, amp_array)
        audio_signal.append(wave)
        
    return np.concatenate(audio_signal) if audio_signal else np.array([])

def mix_music_pattern(pattern_data, all_sfx):
    """Mixes 4 simultaneous audio channels into a master audio track."""
    sfx_dict = {sfx["id"]: sfx for sfx in all_sfx}
    channels_audio = []
    
    for ch_key in ["ch1", "ch2", "ch3", "ch4"]:
        sfx_id = pattern_data.get(ch_key, 64)
        if sfx_id < 64 and sfx_id in sfx_dict:
            channels_audio.append(synth_sfx(sfx_dict[sfx_id], all_sfx))
        else:
            channels_audio.append(np.array([]))

    max_length = max([len(wave) for wave in channels_audio] + [0])
    if max_length == 0: 
        return None 

    master_mix = np.zeros(max_length)
    for wave in channels_audio:
        if len(wave) > 0:
            master_mix += np.pad(wave, (0, max_length - len(wave)), mode='constant')

    # Apply soft limiter to prevent audio clipping
    max_amplitude = np.max(np.abs(master_mix))
    if max_amplitude > 0.95:
        master_mix = (master_mix / max_amplitude) * 0.95
        
    return master_mix

def main():
    print("🚀 Starting DSP synthesis engine (SFX & Music)...")
    
    if not os.path.exists(AUDIO_DIR):
        print(f"❌ Directory not found: {AUDIO_DIR}")
        return

    for tid in os.listdir(AUDIO_DIR):
        audio_game_dir = os.path.join(AUDIO_DIR, tid)
        json_path = os.path.join(audio_game_dir, "audio.json")
        
        if not os.path.exists(json_path):
            continue
            
        with open(json_path, 'r', encoding='utf-8') as f:
            audio_data = json.load(f)
            
        all_sfx = audio_data.get("sfx", [])
        all_music = audio_data.get("music", [])
        
        # --- Stage 1: Render sound effects (SFX) ---
        sfx_out_dir = os.path.join(audio_game_dir, "sfx")
        sfx_rendered = 0
        
        for sfx in all_sfx:
            # Check if SFX has audible content
            if any(note["volume"] > 0 for note in sfx["notes"]):
                os.makedirs(sfx_out_dir, exist_ok=True)
                
                wave = synth_sfx(sfx, all_sfx)
                if len(wave) > 0:
                    wav_int16 = np.int16(wave * 32767)
                    write(os.path.join(sfx_out_dir, f"sfx_{sfx['id']:02d}.wav"), SAMPLE_RATE, wav_int16)
                    sfx_rendered += 1

        # --- Stage 2: Render music tracks ---
        music_out_dir = os.path.join(audio_game_dir, "music")
        music_rendered = 0
        
        for pattern in all_music:
            if pattern["ch1"] < 64 or pattern["ch2"] < 64 or pattern["ch3"] < 64 or pattern["ch4"] < 64:
                os.makedirs(music_out_dir, exist_ok=True)
                
                master_mix = mix_music_pattern(pattern, all_sfx)
                if master_mix is not None:
                    wav_int16 = np.int16(master_mix * 32767)
                    write(os.path.join(music_out_dir, f"music_{pattern['id']:02d}.wav"), SAMPLE_RATE, wav_int16)
                    music_rendered += 1
                    
        print(f"✅ TID {tid}: {sfx_rendered} SFX and {music_rendered} music tracks rendered.")

if __name__ == "__main__":
    main()