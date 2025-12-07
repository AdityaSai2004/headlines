# %%
import feedparser

# Replace the URL below with the RSS feed URL you want to read
rss_url = "https://bullrich.dev/tldr-rss/tech.rss"

feed = feedparser.parse(rss_url)

# for entry in feed.entries:
#     print(f"Title: {entry.title}")
#     print(f"Link: {entry.link}")
#     print(f"Published: {entry.published}")
#     print(f"Summary: {entry.summary}\n")

# %%
from datetime import datetime, timezone

# Get today's date in UTC
today = datetime.now(timezone.utc).date()

# Filter entries published today
today_entries = [
    entry for entry in feed.entries
    if 'published_parsed' in entry and
       datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).date() == today
]

for entry in today_entries:
    print(f"Title: {entry.title}")
    print(f"Link: {entry.link}")
    print(f"Published: {entry.published}")
    print(f"Summary: {entry.summary}\n")

# %%
todays_entries_filtered = [{'title': entry['title'], 'summary': entry['summary']} for entry in today_entries]

# %%
print(todays_entries_filtered)

# %%
# To run this code you need to install the following dependencies:
# pip install google-genai

import base64
import os
from google import genai
from google.genai import types

def generate():
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.5-flash"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=str(todays_entries_filtered)),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        thinking_config = types.ThinkingConfig(
            thinking_budget=-1,
        ),
        response_mime_type="text/plain",
        system_instruction=[
            types.Part.from_text(text="""Role: You are a scriptwriter for a tech podcast featuring two hosts: Alex and Sam. Alex is more analytical and reserved, while Sam is energetic and witty.

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
Sam : bla bla bla"""),
        ],
    )
    script = """"""
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        script += chunk.text
    return script
if __name__ == "__main__":
    scripts = generate()


# %%
with open("podcast_script.txt", "w", encoding="utf-8") as f:
    f.write(scripts)
print("Script saved to podcast_script.txt")

# %%
with open("podcast_script.txt", "r", encoding="utf-8") as file:
    scripts = file.read()
print(scripts)

# %%
from google import genai
from google.genai import types
import wave

# Set up the wave file to save the output:
def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
   with wave.open(filename, "wb") as wf:
      wf.setnchannels(channels)
      wf.setsampwidth(sample_width)
      wf.setframerate(rate)
      wf.writeframes(pcm)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

prompt = scripts

response = client.models.generate_content(
   model="gemini-2.5-flash-preview-tts",
   contents=prompt,
   config=types.GenerateContentConfig(
      response_modalities=["AUDIO"],
      speech_config=types.SpeechConfig(
         multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
            speaker_voice_configs=[
               types.SpeakerVoiceConfig(
                  speaker='Sam',
                  voice_config=types.VoiceConfig(
                     prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name='Fenrir',
                     )
                  )
               ),
               types.SpeakerVoiceConfig(
                  speaker='Alex',
                  voice_config=types.VoiceConfig(
                     prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name='Charon',
                     )
                  )
               ),
            ]
         )
      )
   )
)

data = response.candidates[0].content.parts[0].inline_data.data

file_name='out.wav'
wave_file(file_name, data) # Saves the file to current directory

# %%
import requests
import os
import dotenv
dotenv.load_dotenv()

# %%
def send_to_telegram(audio_file_path, caption="Here's your daily tech podcast!"):
    bot_token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    url = f"https://api.telegram.org/bot{bot_token}/sendAudio"
    
    with open(audio_file_path, 'rb') as f:
        files = {'audio': f}
        data = {'chat_id': chat_id, 'caption': caption}
        response = requests.post(url, files=files, data=data)
        print(response.json())
        
send_to_telegram(file_name)


