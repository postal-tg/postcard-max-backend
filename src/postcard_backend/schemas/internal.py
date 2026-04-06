from pydantic import BaseModel


class SummaryCard(BaseModel):
    users: int
    prompts: int
    blocked_prompts: int
    generations: int
    failed_generations: int
    active_generations: int


class RecentGeneration(BaseModel):
    generation_id: int
    prompt_id: int
    user_id: int
    username: str | None = None
    status: str
    preview_text: str
    image_url: str | None = None
    created_at: str


class SummaryResponse(BaseModel):
    totals: SummaryCard
    recent_generations: list[RecentGeneration]
