import logging
import httpx
from typing import Dict, Any, Tuple
from app.core.config import settings

logger = logging.getLogger(__name__)

class RemediationExecutorService:
    async def execute_allow_listed_action(
        self,
        executor_key: str,
        parameters: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        demo_url = settings.DEMO_APP_URL.rstrip("/")

        # Fixed, compiled dispatch table - ZERO shell execution, ZERO dynamic eval!
        if executor_key == "restart_demo_service":
            return await self._exec_restart(demo_url)
        elif executor_key == "clear_demo_cache":
            return await self._exec_clear_cache(demo_url)
        elif executor_key == "rollback_demo_config":
            return await self._exec_rollback_config(demo_url)
        else:
            raise ValueError(f"Unrecognized remediation executor key '{executor_key}'. Action rejected.")

    async def _exec_restart(self, base_url: str) -> Tuple[bool, Dict[str, Any]]:
        url = f"{base_url}/admin/restart"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url)
                if resp.status_code == 200:
                    return True, resp.json()
                return False, {"error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            logger.error(f"Restart action failed: {e}")
            return False, {"error": str(e)}

    async def _exec_clear_cache(self, base_url: str) -> Tuple[bool, Dict[str, Any]]:
        url = f"{base_url}/admin/clear-cache"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url)
                if resp.status_code == 200:
                    return True, resp.json()
                return False, {"error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            logger.error(f"Clear cache action failed: {e}")
            return False, {"error": str(e)}

    async def _exec_rollback_config(self, base_url: str) -> Tuple[bool, Dict[str, Any]]:
        url = f"{base_url}/admin/rollback-config"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url)
                if resp.status_code == 200:
                    return True, resp.json()
                return False, {"error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            logger.error(f"Rollback config action failed: {e}")
            return False, {"error": str(e)}

remediation_executor = RemediationExecutorService()
