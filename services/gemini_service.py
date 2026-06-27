from google import genai
import json
import asyncio
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

async def get_reply_suggestions(messages: list[dict], my_username: str) -> list[str]:
    context = "\n".join(
        f"{m['sender_name']}: {m['content']}"
        for m in messages[-10:]
        if m.get("type", "text") == "text"
    )

    prompt = f"""You are a smart chat assistant helping {my_username} reply in a conversation.

Conversation:
{context}

Suggest exactly 3 short, natural reply options for {my_username}.
Rules:
- Each reply must be under 12 words
- Match the tone of the conversation (casual, formal, etc.)
- Replies should be different from each other
- Return ONLY a valid JSON array of 3 strings, nothing else

Example output: ["Sounds good!", "Sure, let me check.", "I'll get back to you."]"""

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        ),
    )

    text = response.text.strip()

    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    suggestions = json.loads(text)
    return suggestions[:3]
