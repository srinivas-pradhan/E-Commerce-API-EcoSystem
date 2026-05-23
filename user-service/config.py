from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    auth0_domain: str = "dev-lqyjuexwhe1bupvs.us.auth0.com"
    auth0_client_id: str = "hG5aklxMlkilsmsfF6HjuROKNsivDJLU"
    auth0_client_secret: SecretStr | None = None
    auth0_audience: str = Field(
        default="hG5aklxMlkilsmsfF6HjuROKNsivDJLU",
        description="Auth0 API audience. Defaults to the configured client id.",
    )
    auth0_algorithms: list[str] = ["RS256"]

    model_config = SettingsConfigDict()

    @field_validator("auth0_client_secret", mode="before")
    @classmethod
    def empty_secret_is_not_configured(cls, value: str | None) -> str | None:
        if value == "":
            return None
        return value

    @property
    def auth0_issuer(self) -> str:
        return f"https://{self.auth0_domain}/"

    @property
    def auth0_jwks_url(self) -> str:
        return f"{self.auth0_issuer}.well-known/jwks.json"

settings = Settings()
