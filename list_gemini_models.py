import asyncio
import os
import httpx


async def list_models():
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("No API key found.")
        return

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            models = response.json()
            print("Available models:")
            for m in models.get("models", []):
                print(
                    f"- {m['name']} (supported methods: {m.get('supportedGenerationMethods')})"
                )
        else:
            print(f"Error {response.status_code}: {response.text}")


if __name__ == "__main__":
    asyncio.run(list_models())
