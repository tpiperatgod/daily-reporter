"""Configuration management for xndctl CLI."""

import os
from pathlib import Path
from typing import Optional
import yaml
from pydantic import BaseModel, Field


class APIConfig(BaseModel):
    """API configuration."""
    base_url: str = Field(default="http://localhost:8000", description="API base URL")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")


class OutputConfig(BaseModel):
    """Output configuration."""
    default_format: str = Field(default="table", description="Default output format")
    color: bool = Field(default=True, description="Enable colored output")


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO", description="Log level")


class Config(BaseModel):
    """Main configuration model."""
    api: APIConfig = Field(default_factory=APIConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def get_config_path() -> Path:
    """Get path to config file."""
    config_dir = Path.home() / ".xndctl"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.yaml"


def load_config() -> Config:
    """Load configuration from file or create default."""
    config_path = get_config_path()

    if not config_path.exists():
        # Create default config
        config = Config()
        save_config(config)
        return config

    try:
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)
            if data is None:
                data = {}
            return Config(**data)
    except Exception as e:
        raise RuntimeError(f"Failed to load config from {config_path}: {e}")


def save_config(config: Config) -> None:
    """Save configuration to file."""
    config_path = get_config_path()

    with open(config_path, "w") as f:
        yaml.dump(
            config.model_dump(),
            f,
            default_flow_style=False,
            sort_keys=False
        )


def init_config(base_url: Optional[str] = None, interactive: bool = True) -> Config:
    """Initialize configuration interactively or with provided values."""
    import click

    config = Config()

    if interactive:
        click.echo("Initializing xndctl configuration...")
        click.echo()

        # API configuration
        default_url = base_url or config.api.base_url
        api_url = click.prompt(
            "API base URL",
            default=default_url,
            type=str
        )
        config.api.base_url = api_url

        timeout = click.prompt(
            "Request timeout (seconds)",
            default=config.api.timeout,
            type=int
        )
        config.api.timeout = timeout

        verify_ssl = click.confirm(
            "Verify SSL certificates?",
            default=config.api.verify_ssl
        )
        config.api.verify_ssl = verify_ssl

        # Output configuration
        output_format = click.prompt(
            "Default output format",
            default=config.output.default_format,
            type=click.Choice(["table", "json", "yaml"])
        )
        config.output.default_format = output_format

        color = click.confirm(
            "Enable colored output?",
            default=config.output.color
        )
        config.output.color = color

        click.echo()
    else:
        if base_url:
            config.api.base_url = base_url

    # Save configuration
    save_config(config)
    config_path = get_config_path()

    if interactive:
        click.echo(f"Configuration saved to: {config_path}")

    return config


def update_config(**kwargs) -> Config:
    """Update specific config values."""
    config = load_config()

    # Update API settings
    if "base_url" in kwargs:
        config.api.base_url = kwargs["base_url"]
    if "timeout" in kwargs:
        config.api.timeout = kwargs["timeout"]
    if "verify_ssl" in kwargs:
        config.api.verify_ssl = kwargs["verify_ssl"]

    # Update output settings
    if "default_format" in kwargs:
        config.output.default_format = kwargs["default_format"]
    if "color" in kwargs:
        config.output.color = kwargs["color"]

    # Update logging settings
    if "log_level" in kwargs:
        config.logging.level = kwargs["log_level"]

    save_config(config)
    return config
