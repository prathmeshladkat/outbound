import asyncio
from time import perf_counter

from google import genai

from app.core.config import settings


async def main():
    client = genai.Client(api_key=settings.gemini_api_key)

    for attempt in range(1, 4):
        start = perf_counter()
        first_token_at = None
        chunks = []

        print(f"\nAttempt {attempt}")

        try:
            stream = await client.aio.models.generate_content_stream(
                model="gemini-3.5-flash-lite",
                contents=(
                    "You are a healthcare insurance voice agent. "
                    "The caller says: Hello, I want to check "
                    "the status of an insurance claim. "
                    "Reply in one short sentence."
                ),
            )

            async for chunk in stream:
                if chunk.text:
                    if first_token_at is None:
                        first_token_at = perf_counter()
                        print(
                            "First text chunk:",
                            f"{first_token_at - start:.2f}s",
                        )

                    chunks.append(chunk.text)

            print(f"Total time: {perf_counter() - start:.2f}s")
            print("Response:", "".join(chunks))

        except Exception as exc:
            print(
                f"Failed after {perf_counter() - start:.2f}s:",
                type(exc).__name__,
                str(exc),
            )


asyncio.run(main())