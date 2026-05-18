"""Dimension 2: Event-Driven Integration Testing (Interaction Level)

ตรวจสอบการไหลของ events ผ่าน RuntimeEventBus ระหว่าง agent layers:
HypothesisAgent → CritiqueAgent → SynthesisAgent → MemoryAgent
รวมถึง isolation ของ failing handlers
"""
import asyncio

import pytest

from src.infrastructure.event_bus import (
    TOPIC_HYPOTHESIS_CRITIQUED,
    TOPIC_HYPOTHESIS_GENERATED,
    TOPIC_SYNTHESIS_READY,
    RuntimeEvent,
    RuntimeEventBus,
)


# ─── Full pipeline flow ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_hypothesis_to_synthesis_pipeline_event_flow():
    """จำลอง pipeline สมบูรณ์: hypothesis → critique → synthesis ทุก stage รับ event"""
    bus = RuntimeEventBus()
    log: list[str] = []

    async def on_hypothesis(event: RuntimeEvent) -> None:
        log.append(f"critique_received:{event.topic}")

    async def on_critique(event: RuntimeEvent) -> None:
        log.append(f"synthesis_received:{event.topic}")

    async def on_synthesis(event: RuntimeEvent) -> None:
        log.append(f"memory_received:{event.topic}")

    bus.subscribe(TOPIC_HYPOTHESIS_GENERATED, on_hypothesis)
    bus.subscribe(TOPIC_HYPOTHESIS_CRITIQUED, on_critique)
    bus.subscribe(TOPIC_SYNTHESIS_READY, on_synthesis)

    for topic in (TOPIC_HYPOTHESIS_GENERATED, TOPIC_HYPOTHESIS_CRITIQUED, TOPIC_SYNTHESIS_READY):
        await bus.publish(RuntimeEvent(topic=topic, source_agent_id="pipeline", payload={}))

    assert log == [
        f"critique_received:{TOPIC_HYPOTHESIS_GENERATED}",
        f"synthesis_received:{TOPIC_HYPOTHESIS_CRITIQUED}",
        f"memory_received:{TOPIC_SYNTHESIS_READY}",
    ]


@pytest.mark.asyncio
async def test_multiple_subscribers_all_receive():
    """หลาย subscriber บน topic เดียวกัน ต้องได้รับทุกคน (fan-out)"""
    bus = RuntimeEventBus()
    counters = {"a": 0, "b": 0, "c": 0}

    async def sub_a(event: RuntimeEvent) -> None:
        counters["a"] += 1

    async def sub_b(event: RuntimeEvent) -> None:
        counters["b"] += 1

    async def sub_c(event: RuntimeEvent) -> None:
        counters["c"] += 1

    for sub in (sub_a, sub_b, sub_c):
        bus.subscribe(TOPIC_HYPOTHESIS_GENERATED, sub)

    await bus.publish(
        RuntimeEvent(
            topic=TOPIC_HYPOTHESIS_GENERATED,
            source_agent_id="HypothesisAgent",
            payload={"statement": "test"},
        )
    )
    assert counters == {"a": 1, "b": 1, "c": 1}


@pytest.mark.asyncio
async def test_failing_handler_does_not_block_other_handlers():
    """Handler ที่ throw exception ต้องถูก isolate — handler ตัวอื่นยังทำงาน"""
    bus = RuntimeEventBus()
    healthy_received: list[bool] = []

    async def failing_handler(event: RuntimeEvent) -> None:
        raise RuntimeError("Simulated crash in handler")

    async def healthy_handler(event: RuntimeEvent) -> None:
        healthy_received.append(True)

    bus.subscribe(TOPIC_SYNTHESIS_READY, failing_handler)
    bus.subscribe(TOPIC_SYNTHESIS_READY, healthy_handler)

    # ต้องไม่ raise — RuntimeEventBus ต้อง swallow handler errors
    await bus.publish(
        RuntimeEvent(topic=TOPIC_SYNTHESIS_READY, source_agent_id="SynthesisAgent", payload={})
    )

    assert healthy_received == [True]


@pytest.mark.asyncio
async def test_global_wildcard_captures_all_events():
    """Subscribe ด้วย '*' ต้องรับทุก topic"""
    bus = RuntimeEventBus()
    all_topics: list[str] = []

    async def catch_all(event: RuntimeEvent) -> None:
        all_topics.append(event.topic)

    bus.subscribe("*", catch_all)

    topics = [TOPIC_HYPOTHESIS_GENERATED, TOPIC_HYPOTHESIS_CRITIQUED, TOPIC_SYNTHESIS_READY]
    for topic in topics:
        await bus.publish(RuntimeEvent(topic=topic, source_agent_id="X", payload={}))

    assert all_topics == topics


@pytest.mark.asyncio
async def test_event_payload_delivered_intact():
    """Payload ต้องถึง handler โดยไม่มีข้อมูลสูญหาย"""
    bus = RuntimeEventBus()
    payloads: list[dict] = []

    async def capture(event: RuntimeEvent) -> None:
        payloads.append(event.payload)

    bus.subscribe(TOPIC_HYPOTHESIS_GENERATED, capture)
    expected = {"statement": "AI hypothesis", "confidence": 0.92, "generation": 3}

    await bus.publish(
        RuntimeEvent(
            topic=TOPIC_HYPOTHESIS_GENERATED,
            source_agent_id="HypothesisAgent",
            payload=expected,
        )
    )
    assert payloads[0] == expected


@pytest.mark.asyncio
async def test_concurrent_publish_all_delivered():
    """ส่ง events พร้อมกัน 50 ใบ — ต้องครบทุกใบ (ไม่มี race condition)"""
    bus = RuntimeEventBus()
    received: list[int] = []

    async def handler(event: RuntimeEvent) -> None:
        received.append(event.payload["seq"])

    bus.subscribe(TOPIC_HYPOTHESIS_GENERATED, handler)

    await asyncio.gather(
        *[
            bus.publish(
                RuntimeEvent(
                    topic=TOPIC_HYPOTHESIS_GENERATED,
                    source_agent_id="Agent",
                    payload={"seq": i},
                )
            )
            for i in range(50)
        ]
    )
    assert len(received) == 50
    assert sorted(received) == list(range(50))
