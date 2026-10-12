import logging
from typing import List, Dict, Any
from app.services.detection import detection_service
from app.services.grouping import grouping_service

logger = logging.getLogger(__name__)

async def run_detection_pipeline(events: List[Dict[str, Any]]):
    try:
        matches = await detection_service.evaluate_events(events)
        if matches:
            incident_ids = await grouping_service.correlate_and_group(matches)
            logger.info(f"Detection pipeline created/updated {len(incident_ids)} incidents from {len(events)} events")
            return incident_ids
        return []
    except Exception as e:
        logger.error(f"Error executing detection pipeline: {e}", exc_info=True)
        return []
