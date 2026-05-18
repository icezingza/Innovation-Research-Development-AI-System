import asyncio
import logging
import sys
from src.memory.research_memory import ResearchMemory, MemoryEntry

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("test_memory")


async def test_memory_persistence():
    print("\n" + "🧠" * 5)
    print("🧠 กำลังทดสอบระบบความจำ (Memory Integration)...")
    print("🧠" * 5 + "\n")

    # 1. Setup Memory Engine (In-memory mode for this test since DBs aren't connected)
    memory = ResearchMemory()
    test_topic = "ความลับของโปรเจกต์ NamoNexus"
    test_fact = "นะโมชอบใช้โหมด Fast ทำงานเบื้องต้นเสมอเพื่อประหยัด Token"

    # 2. Store: บันทึกข้อมูล
    print(f"📥 กำลังบันทึกข้อมูล: '{test_fact}'")
    entry = MemoryEntry(
        topic=test_topic,
        statement=test_fact,
        confidence=1.0,
        source="test_script",
        session_id="test_session",
    )
    await memory.store(entry)

    # Simulate indexing delay
    await asyncio.sleep(1)

    # 3. Recall: ลองถามกลับ
    query = "นะโมชอบใช้โหมด Fast ทำงาน"
    print(f"🔍 กำลังค้นคืนความจำด้วยคำถาม: '{query}'")
    # Using 'recall' method as defined in src/memory/research_memory.py
    results = await memory.recall(query, limit=1)

    # 4. Validation
    if results and test_fact in results[0].statement:
        print("\n✅ [PASS] ระบบจำข้อมูลและค้นคืนได้ถูกต้องแม่นยำ!")
        print(f"   Match found: {results[0].statement}")
    else:
        print("\n❌ [FAIL] ระบบค้นคืนข้อมูลไม่พบ หรือข้อมูลไม่ตรง")
        if results:
            print(f"   ผลลัพธ์ที่ได้คือ: {results[0].statement}")
        else:
            print("   ไม่พบผลลัพธ์ใดๆ")
    print("\n" + "=" * 50)


if __name__ == "__main__":
    asyncio.run(test_memory_persistence())
