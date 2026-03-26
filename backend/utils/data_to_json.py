import asyncio
import json
from datetime import date
from typing import List, Sequence

from .database import AsyncItemRepository


def _serialize_dates(records: List[dict]) -> List[dict]:
	serialized: List[dict] = []
	for record in records:
		normalized = dict(record)
		if isinstance(normalized.get("date"), date):
			normalized["date"] = normalized["date"].isoformat()
		serialized.append(normalized)
	return serialized


async def records_by_ids_to_json(ids: Sequence[int], db_path: str = "data.db") -> str:
	"""Fetch records for the provided IDs and return them as a JSON string."""
	repo = AsyncItemRepository(db_path)

	records: List[dict] = []
	for item_id in ids:
		row = await repo.get_by_id(item_id)
		if row is not None:
			records.append(row)

	return json.dumps(_serialize_dates(records), indent=2)


def records_by_ids_to_json_sync(ids: Sequence[int], db_path: str = "data.db") -> str:
	"""Synchronous wrapper around records_by_ids_to_json."""
	try:
		asyncio.get_running_loop()
	except RuntimeError:
		return asyncio.run(records_by_ids_to_json(ids, db_path))

	raise RuntimeError(
		"records_by_ids_to_json_sync cannot run inside an active event loop. "
		"Use 'await records_by_ids_to_json(...)' instead."
	)
