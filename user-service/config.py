from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    auth_key: str = 'default_value'
    
    # Configuration for the settings, such as environment variable prefixes
    model_config = SettingsConfigDict(env_prefix='my_prefix_', env_file='.env')

# Instantiating this will read from environment variables (e.g., MY_PREFIX_AUTH_KEY)
settings = Settings()
