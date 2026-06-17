from supabase import create_client


class Database:
    def __init__(self, url: str, service_key: str):
        self._client = create_client(url, service_key)

    def get_active_picks(self) -> list:
        response = self._client.table("active_picks").select("*").execute()
        return response.data

    def insert_active_pick(self, pick: dict) -> None:
        self._client.table("active_picks").insert(pick).execute()

    def close_position(self, pick_id: int, exit_data: dict) -> None:
        pick = (
            self._client.table("active_picks")
            .select("*")
            .eq("id", pick_id)
            .single()
            .execute()
            .data
        )
        history_row = {
            "ticker": pick["ticker"],
            "entry_date": pick["entry_date"],
            "entry_price": pick["entry_price"],
            "qty": pick["qty"],
            "reasoning": pick["reasoning"],
            **exit_data,
        }
        self._client.table("trade_history").insert(history_row).execute()
        self._client.table("active_picks").delete().eq("id", pick_id).execute()

    def get_trade_history_summary(self) -> dict:
        response = self._client.table("trade_history").select("realized_pnl_pct").execute()
        rows = response.data
        total_pnl_pct = sum(row["realized_pnl_pct"] for row in rows) if rows else 0.0
        return {"closed_trades": len(rows), "total_realized_pnl_pct": round(total_pnl_pct, 10)}
