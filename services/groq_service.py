from groq import AsyncGroq
import json
from config import GROQ_API_KEY

client = AsyncGroq(api_key=GROQ_API_KEY)

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

    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )

    text = response.choices[0].message.content.strip()

    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    suggestions = json.loads(text)
    return suggestions[:3]
