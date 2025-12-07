import os
import wave
from datetime import datetime, timezone
import feedparser
import requests

from google import genai
from google.genai import types


RSS_URL = "https://bullrich.dev/tldr-rss/tech.rss"


def get_today_entries(rss_url: str):
    """Fetch RSS and return today's entries (UTC-based)."""
    feed = feedparser.parse(rss_url)
    today = datetime.now(timezone.utc).date()

    today_entries = []
    for entry in feed.entries:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            published_dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            if published_dt.date() == today:
                today_entries.append(
                    {
                        "title": entry.title,
                        "summary": entry.summary,
                    }
                )

    return today_entries


def build_podcast_script(entries):
    """Call Gemini to turn entries into a 2-host script."""
    if not entries:
        # Fallback – you can tweak this behavior
        entries = [{"title": "Slow news day", "summary": "No major tech headlines today."}]

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=str(entries))],
        ),
    ]

    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=-1),
        response_mime_type="text/plain",
        system_instruction=[
            types.Part.from_text(
                text="""Role: You are a scriptwriter for a tech podcast featuring two hosts: Alex and Sam. Alex is more analytical and reserved, while Sam is energetic and witty.

Task: Convert the following tech news items (title + summary) into a dynamic, conversational podcast script between Alex and Sam. They should discuss each news item in an engaging way: adding opinions, asking questions, clarifying points, and occasionally making light-hearted jokes or analogies.

Keep the tone friendly and natural, like two smart friends catching up on the day's tech headlines. Limit each topic to ~1–2 minutes of dialogue. The conversation should flow logically, with good transitions between topics.

Include:

Natural back-and-forth dialogue (no monologues)

Occasional reactions (e.g., “Whoa, seriously?” or “That makes sense.”)

Personality consistency (Alex = thoughtful, Sam = punchy/funny)

The output should contain Name, theme of the podcast. Names of the hosts and characteristics of each 
Eg : "Tech Talk  From Apps to Orbit Hosts Alex (Analytical, Reserved) & Sam (Energetic, Witty)"
DONOT include colons anywhere other than to mention speaker and what the speaker says.
The conversation output part should be strictly like 
Alex : bla bla bla 
Sam : bla bla bla"""
            ),
        ],
    )

    script = ""
    for chunk in client.models.generate_content_stream(
        model="gemini-2.5-flash", contents=contents, config=config
    ):
        script += chunk.text

    return script


def save_wave(filename, pcm, channels=1, rate=24000, sample_width=2):
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)


def tts_from_script(script: str, filename: str = "out.wav") -> str:
    """Use Gemini multi-speaker TTS to generate an audio file."""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=script,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                    speaker_voice_configs=[
                        types.SpeakerVoiceConfig(
                            speaker="Sam",
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name="Fenrir",
                                )
                            ),
                        ),
                        types.SpeakerVoiceConfig(
                            speaker="Alex",
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name="Charon",
                                )
                            ),
                        ),
                    ]
                )
            ),
        ),
    )

    pcm = response.candidates[0].content.parts[0].inline_data.data
    save_wave(filename, pcm)
    return filename


def send_to_telegram(audio_file_path, caption="Here's your daily tech podcast!"):
    bot_token = os.environ["BOT_TOKEN"]
    chat_id = os.environ["CHAT_ID"]

    url = f"https://api.telegram.org/bot{bot_token}/sendAudio"
    with open(audio_file_path, "rb") as f:
        files = {"audio": f}
        data = {"chat_id": chat_id, "caption": caption}
        response = requests.post(url, files=files, data=data)

    print("Telegram response:", response.status_code, response.text)


def main():
    entries = get_today_entries(RSS_URL)
    print(f"Found {len(entries)} entries for today")
    script = build_podcast_script(entries)

    # Optional: basic sanity check for speaker tags
    if "Alex" not in script or "Sam" not in script:
        print("Warning: script might be missing speaker tags")

    audio_path = tts_from_script(script, filename="out.wav")
    send_to_telegram(audio_path)


if __name__ == "__main__":
    main()
