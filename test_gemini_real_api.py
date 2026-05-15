import asyncio
import os
from src.inference.gemini_provider import GeminiProvider
from src.inference.base_provider import CompletionRequest

# Try to load .env manually if it exists but wasn't detected
def load_env():
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value

async def test_gemini_live():
    print("\n" + "🚀" * 5)
    print("🚀 กำลังทดสอบ Gemini Provider (Real API)...")
    print("🚀" * 5 + "\n")
    
    load_env()
    
    # ดึง API Key จาก Environment
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ ไม่พบ API Key! กรุณา set GEMINI_API_KEY ก่อน")
        print("   (คุณสามารถสร้างไฟล์ .env และใส่ GEMINI_API_KEY=your_key_here)")
        return

    # 1. Initialize Provider
    # ลองใช้รุ่น Lite ที่น่าจะมีโควตาเหลือ
    provider = GeminiProvider(api_key=api_key, model="gemini-2.0-flash-lite")
    
    # 2. Prepare Request
    request = CompletionRequest(
        prompt="ช่วยสรุปสั้นๆ ใน 1 ประโยคว่าระบบ AI Agent Swarm คืออะไร?",
        system="คุณคือผู้เชี่ยวชาญด้าน AI สถาปัตยกรรมระดับสูง",
        temperature=0.1
    )

    # 3. Execute
    print(f"📡 กำลังส่งคำขอไปที่ {provider.name} (model: gemini-2.0-flash-lite)...")
    try:
        response = await provider.complete(request)
        
        # 4. Validation
        print("\n✅ [SUCCESS] การเรียก API สำเร็จ!")
        print(f"📝 ผลลัพธ์: {response.content}")
        print(f"📊 โมเดลที่ใช้: {response.model}")
        if response.tokens_used:
            print(f"💎 จำนวน Token ที่ใช้: {response.tokens_used}")
            
    except Exception as e:
        print(f"\n❌ [ERROR] การเรียก API ล้มเหลว: {str(e)}")
    
    print("\n" + "="*50)

if __name__ == "__main__":
    asyncio.run(test_gemini_live())
