import os
import re
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
DATA_DIR = os.environ.get("PICO8_DATA_DIR", os.path.join(PROJECT_ROOT, "dataset_pico8"))

# Directory configurations
P8_DIR = os.path.join(DATA_DIR, "p8")
AUDIO_DIR = os.path.join(DATA_DIR, "audio")

def extract_audio_data(p8_path):
    """Reads the .p8 file and parses __sfx__ and __music__ into structured JSON."""
    with open(p8_path, 'r', encoding='utf-8') as f:
        content = f.read()

    audio_data = {
        "sfx": [],
        "music": []
    }

    # --- 1. PARSE SFX ---
    # Each SFX line is up to 168 hex chars.
    # Chars 0-1: Editor mode | 2-3: Speed | 4-5: Loop Start | 6-7: Loop End
    # Chars 8 to 167: 32 notes (5 chars each: Pitch(2) + Instrument(1) + Volume(1) + Effect(1))
    sfx_match = re.search(r'__sfx__\n(.*?)(?:__\w+__|$)', content, re.DOTALL)
    if sfx_match:
        sfx_lines = sfx_match.group(1).strip().split('\n')
        for sfx_id, line in enumerate(sfx_lines):
            line = line.strip().ljust(168, '0')[:168]
            
            sfx_obj = {
                "id": sfx_id,
                "speed": int(line[2:4], 16),
                "loop_start": int(line[4:6], 16),
                "loop_end": int(line[6:8], 16),
                "notes": []
            }
            
            for i in range(32):
                offset = 8 + (i * 5)
                note_hex = line[offset:offset+5]
                
                note_obj = {
                    "pitch": int(note_hex[0:2], 16),
                    "instrument": int(note_hex[2], 16),
                    "volume": int(note_hex[3], 16),
                    "effect": int(note_hex[4], 16)
                }
                sfx_obj["notes"].append(note_obj)
                
            audio_data["sfx"].append(sfx_obj)

    # --- 2. PARSE MUSIC ---
    # Each Music line is 11 hex chars.
    # Chars 0-1: Flags | 2-3: Ch1 | 4-5: Ch2 | 6-7: Ch3 | 8-9: Ch4
    music_match = re.search(r'__music__\n(.*?)(?:__\w+__|$)', content, re.DOTALL)
    if music_match:
        music_lines = music_match.group(1).strip().split('\n')
        for music_id, line in enumerate(music_lines):
            # Strip whitespace before parsing fixed character offsets
            line = line.replace(' ', '').strip().ljust(10, '0')[:10]
            
            music_obj = {
                "id": music_id,
                "flags": int(line[0:2], 16),
                "ch1": int(line[2:4], 16),
                "ch2": int(line[4:6], 16),
                "ch3": int(line[6:8], 16),
                "ch4": int(line[8:10], 16)
            }
            audio_data["music"].append(music_obj)

    # If both sections are empty, return None
    if not audio_data["sfx"] and not audio_data["music"]:
        return None
        
    return audio_data

def main():
    print("🎵 Starting Audio extraction...")
    print(f"📂 Reading .p8 from: {P8_DIR}")
    print(f"📂 Saving to: {AUDIO_DIR}")
    
    if not os.path.exists(P8_DIR):
        print(f"❌ Directory not found: {P8_DIR}")
        return

    os.makedirs(AUDIO_DIR, exist_ok=True)

    processed_count = 0
    
    for tid in os.listdir(P8_DIR):
        p8_dir = os.path.join(P8_DIR, tid)
        if not os.path.isdir(p8_dir):
            continue
        
        p8_file = os.path.join(p8_dir, f"{tid}.p8")
        if not os.path.exists(p8_file):
            continue
        
        audio_data = extract_audio_data(p8_file)
        
        if audio_data:
            audio_out_dir = os.path.join(AUDIO_DIR, tid)
            os.makedirs(audio_out_dir, exist_ok=True)

            json_path = os.path.join(audio_out_dir, "audio.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(audio_data, f, indent=2) 
                
            print(f"✅ TID {tid}: Audio data converted to JSON successfully.")
            processed_count += 1
        else:
            print(f"⚠️ TID {tid}: Audio sections not found or empty.")

    print(f"\n🎉 Done! {processed_count} games audio processed.")

if __name__ == "__main__":
    main()