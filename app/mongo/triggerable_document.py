from app.hook_details.hook_details import HookDetails


class TriggerableDocument:
    async def should_be_triggered_by(self, hook_details: HookDetails) -> bool:
        raise NotImplementedError()
