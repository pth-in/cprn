from supabase import Client

class LogManager:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client

    def log(self, name, severity="INFO", metadata=None):
        """Sends an ingestion event to Supabase."""
        if not self.supabase:
            print(f"Logging (No Supabase): {name} [{severity}] {metadata or ''}")
            return
        try:
            event = {
                "event_type": "INGESTION",
                "event_name": name,
                "severity": severity,
                "metadata": metadata or {}
            }
            self.supabase.table("system_events").insert(event).execute()
        except Exception as e:
            print(f"Logging Error: {e}")
