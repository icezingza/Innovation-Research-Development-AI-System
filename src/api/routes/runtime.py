from typing import Any

from fastapi import APIRouter, Depends

from src.api.dependencies import get_state_manager
from src.runtime.state_manager import RuntimeStateManager

router = APIRouter(prefix="/runtime", tags=["runtime"])


@router.get("/state")
async def runtime_state(
    manager: RuntimeStateManager = Depends(get_state_manager),
) -> dict[str, Any]:
    return await manager.get_state()
