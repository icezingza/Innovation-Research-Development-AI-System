import pytest
import numpy as np
from testcontainers.qdrant import QdrantContainer
from qdrant_client import QdrantClient
from qdrant_client.http import models

@pytest.fixture(scope="module")
def qdrant_db():
    """เปิด Docker Container สำหรับ Qdrant จริงๆ"""
    with QdrantContainer("qdrant/qdrant:latest") as qdrant:
        host = qdrant.get_container_host_ip()
        port = qdrant.get_exposed_port(6333)
        client = QdrantClient(url=f"http://{host}:{port}")
        yield client

@pytest.mark.asyncio
async def test_advanced_semantic_with_filtering(qdrant_db):
    print("\n🔍 เริ่มการทดสอบ Advanced Semantic Search...")
    
    collection_name = "cognitive_vault"
    vector_size = 128  # จำลองขนาด Embedding

    # 1. สร้าง Collection พร้อมระบุระยะห่างแบบ Cosine
    qdrant_db.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
    )

    # 2. จำลองข้อมูล "Cognitive Fragments" ที่มีความซับซ้อน
    # เราจะใส่ข้อมูลที่มี 'หัวข้อ' และ 'ระดับความมั่นใจ' เข้าไปด้วย
    fragments = [
        {"id": 1, "text": "Empathy Engine: การรับรู้อารมณ์ผ่านน้ำเสียง", "topic": "empathy", "confidence": 0.95},
        {"id": 2, "text": "Inference Router: การเลือกโมเดลตามความยากของงาน", "topic": "infra", "confidence": 0.88},
        {"id": 3, "text": "Empathy Engine: การปรับโทนเสียงให้เข้ากับผู้ใช้", "topic": "empathy", "confidence": 0.70},
    ]

    points = []
    for f in fragments:
        # สร้าง Vector จำลอง (ในงานจริงจะใช้ Gemini/OpenAI Embedding)
        vector = np.random.rand(vector_size).tolist()
        points.append(models.PointStruct(
            id=f["id"],
            vector=vector,
            payload={"text": f["text"], "topic": f["topic"], "confidence": f["confidence"]}
        ))

    qdrant_db.upsert(collection_name=collection_name, points=points)

    # 3. ค้นหาแบบ Advanced: "หาเรื่อง Empathy ที่มีความมั่นใจ > 0.80 เท่านั้น"
    query_vector = np.random.rand(vector_size).tolist()
    
    print("🎯 กำลังค้นหาด้วยเงื่อนไข: Topic = 'empathy' และ Confidence > 0.80")
    
    search_result = qdrant_db.query_points(
        collection_name=collection_name,
        query=query_vector,
        query_filter=models.Filter(
            must=[
                models.FieldCondition(key="topic", match=models.MatchValue(value="empathy")),
                models.FieldCondition(key="confidence", range=models.Range(gt=0.80)),
            ]
        ),
        limit=5,
        search_params=models.SearchParams()
    ).points

    # 4. การตรวจสอบ (Assertions)
    print(f"📊 ผลลัพธ์ที่พบ: {len(search_result)} รายการ")
    
    for res in search_result:
        print(f" - Found: {res.payload['text']} (Score: {res.score:.4f})")
        assert res.payload["topic"] == "empathy"
        assert res.payload["confidence"] > 0.80

    assert len(search_result) <= 1  # ในเคสนี้ควรเจอแค่ ID 1 ตัวเดียว
    print("\n✅ [PASS] การทดสอบ Semantic + Filtering สำเร็จลุล่วง!")
