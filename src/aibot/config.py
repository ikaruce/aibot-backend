from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App identity — used in PR titles, comment headers, template substitution
    app_name: str = "aibot"

    # GitHub App credentials
    github_app_id: str
    github_private_key: str
    github_webhook_secret: str

    # Source repository for reusable workflows and skills
    aicli_repo: str = "ikaruce/ai-cli-workflow"

    # GitHub API base (override for GHES)
    github_base_url: str = "https://github.com"

    # Public URL of this server — baked into the dispatch workflow template
    # so GitHub Actions knows where to call /api/v1/token
    public_url: str

    # Static API key that GitHub Actions uses to call POST /api/v1/token
    api_key: str

    @property
    def github_api_url(self) -> str:
        if "github.com" in self.github_base_url and "api." not in self.github_base_url:
            return "https://api.github.com"
        return f"{self.github_base_url}/api/v3"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
