import aiosqlite
from datetime import date, datetime
from typing import Optional, List, Dict, Any


class AsyncItemRepository:
    def __init__(self, db_path: str = "data.db") -> None:
        self.db_path = db_path

    async def init(self) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS records (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    amount REAL NOT NULL,
                    date TEXT NOT NULL
                )
                """
            )
            await conn.commit()

    @staticmethod
    def _to_iso(d: date) -> str:
        return d.isoformat()

    @staticmethod
    def _to_date(s: str) -> date:
        return datetime.strptime(s, "%Y-%m-%d").date()

    # CREATE
    async def create(self, id: int, name: str, amount: float, dt: date) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                "INSERT INTO records (id, name, amount, date) VALUES (?, ?, ?, ?)",
                (id, name, amount, self._to_iso(dt)),
            )
            await conn.commit()

    # READ (single)
    async def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT id, name, amount, date FROM records WHERE id = ?",
                (id,),
            ) as cur:
                row = await cur.fetchone()
                if not row:
                    return None

                item = dict(row)
                item["date"] = self._to_date(item["date"])
                return item

    # READ (all)
    async def list_all(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT id, name, amount, date FROM records ORDER BY id"
            ) as cur:
                rows = await cur.fetchall()

        items: List[Dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["date"] = self._to_date(item["date"])
            items.append(item)
        return items

    # UPDATE
    async def update(self, id: int, name: str, amount: float, dt: date) -> bool:
        async with aiosqlite.connect(self.db_path) as conn:
            cur = await conn.execute(
                "UPDATE records SET name = ?, amount = ?, date = ? WHERE id = ?",
                (name, amount, self._to_iso(dt), id),
            )
            await conn.commit()
            return cur.rowcount > 0

    # DELETE
    async def delete(self, id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as conn:
            cur = await conn.execute("DELETE FROM records WHERE id = ?", (id,))
            await conn.commit()
            return cur.rowcount > 0


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main() -> None:
        repo = AsyncItemRepository("example_async.db")
        await repo.init()

        await repo.create(1, "Apple", 12.5, date(2026, 3, 25))
        print(await repo.get_by_id(1))
        print(await repo.list_all())

        await repo.update(1, "Green Apple", 15.0, date(2026, 3, 26))
        print(await repo.get_by_id(1))

        await repo.delete(1)
        print(await repo.get_by_id(1))

    asyncio.run(main())