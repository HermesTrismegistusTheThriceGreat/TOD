#!/usr/bin/env python3
"""
Comprehensive Logging Module
Logs to both console and hourly rotating log files for e2e debugging
"""

import logging
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.logging import RichHandler
from rich.text import Text
import sys
import re

# Create logs directory
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Rich console for formatted output
console = Console()


class CredentialRedactionFilter(logging.Filter):
    """
    Redacts API credentials from log records to prevent accidental exposure.
    Matches common credential formats and replaces with masked values.
    """

    # Patterns to match various credential formats
    REDACTION_PATTERNS = [
        # Environment variable formats
        (r'ALPACA_API_KEY\s*=\s*[\w\-\.]+', 'ALPACA_API_KEY=***'),
        (r'ALPACA_SECRET_KEY\s*=\s*[\w\-\.]+', 'ALPACA_SECRET_KEY=***'),
        (r'API_KEY\s*=\s*[\w\-\.]+', 'API_KEY=***'),
        (r'SECRET_KEY\s*=\s*[\w\-\.]+', 'SECRET_KEY=***'),
        (r'ENCRYPTION_KEY\s*=\s*[\w\-\.\/\+]+', 'ENCRYPTION_KEY=***'),

        # JSON/dict formats
        (r'"api[_-]?key"\s*:\s*"[^"]*"', '"api_key":"***"'),
        (r'"secret[_-]?key"\s*:\s*"[^"]*"', '"secret_key":"***"'),
        (r"'api[_-]?key'\s*:\s*'[^']*'", "'api_key':'***'"),
        (r"'secret[_-]?key'\s*:\s*'[^']*'", "'secret_key':'***'"),

        # Query string and URL formats
        (r'[?&]api[_-]?key=[^&\s]*', '?api_key=***'),
        (r'Bearer\s+[\w\-\.]+', 'Bearer ***'),

        # Alpaca-specific key formats (PK... for API key, sp... for secret)
        (r'\bPK[\w]{17,}\b', 'PK***'),
        (r'\bsp[\w]{28,}\b', 'sp***'),

        # Generic high-entropy strings that look like API keys (20+ alphanumeric)
        (r'["\'][\w\-]{32,}["\']', '"***"'),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter a log record to redact credentials.

        Args:
            record: LogRecord to filter

        Returns:
            True (always allow record to be logged, but redacted)
        """
        # Redact message
        if record.msg:
            record.msg = self._redact_string(str(record.msg))

        # Redact formatted args
        try:
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: self._redact_string(str(v)) for k, v in record.args.items()}
                else:
                    record.args = tuple(self._redact_string(str(arg)) for arg in record.args)
        except Exception:
            pass  # Don't break logging if args redaction fails

        # Redact exception traceback
        if record.exc_text:
            record.exc_text = self._redact_string(record.exc_text)

        return True

    def _redact_string(self, text: str) -> str:
        """Apply all redaction patterns to text"""
        for pattern, replacement in self.REDACTION_PATTERNS:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text


class HourlyRotatingFileHandler(logging.Handler):
    """Custom handler that rotates log files every hour"""

    def __init__(self, logs_dir: Path):
        super().__init__()
        self.logs_dir = logs_dir
        self.current_file = None
        self.current_hour = None

    def emit(self, record):
        """Emit a record to the appropriate hourly log file"""
        try:
            # Get current hour timestamp
            now = datetime.now()
            hour_key = now.strftime("%Y-%m-%d_%H")

            # Rotate file if hour changed
            if hour_key != self.current_hour:
                if self.current_file:
                    self.current_file.close()

                log_file_path = self.logs_dir / f"{hour_key}.log"
                self.current_file = open(log_file_path, "a", encoding="utf-8")
                self.current_hour = hour_key

                # Write header for new file
                self.current_file.write(f"\n{'='*80}\n")
                self.current_file.write(
                    f"Log Session Started: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
                self.current_file.write(f"{'='*80}\n\n")

            # Write log message
            log_entry = self.format(record)
            self.current_file.write(log_entry + "\n")
            self.current_file.flush()

        except Exception as e:
            print(f"Error writing to log file: {e}", file=sys.stderr)

    def close(self):
        """Close current log file"""
        if self.current_file:
            self.current_file.close()
        super().close()


class OrchestratorLogger:
    """
    Centralized logger for the orchestrator backend
    Logs to both console (with Rich formatting) and hourly rotating files
    """

    def __init__(self, name: str = "orchestrator"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False  # Don't propagate to root logger

        # Clear existing handlers
        self.logger.handlers.clear()

        # Add Rich console handler
        console_handler = RichHandler(
            console=console,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            markup=True,
        )
        console_handler.setLevel(logging.DEBUG)
        console_formatter = logging.Formatter("%(message)s")
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # Add hourly rotating file handler
        file_handler = HourlyRotatingFileHandler(LOGS_DIR)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Add credential redaction filter to all handlers
        redaction_filter = CredentialRedactionFilter()
        for handler in self.logger.handlers:
            handler.addFilter(redaction_filter)

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(f"[cyan]{message}[/cyan]", **kwargs)

    def success(self, message: str, **kwargs):
        """Log success message"""
        self.logger.info(f"[green]✅ {message}[/green]", **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(f"[yellow]⚠️  {message}[/yellow]", **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(f"[red]❌ {message}[/red]", **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.logger.critical(f"[bold red]🔥 {message}[/bold red]", **kwargs)

    def panel(self, message: str, title: str = "", style: str = "cyan", expand: bool = True):
        """Log a Rich panel (console only, file gets plain text)"""
        # Log to console with Rich panel
        console.print(Panel(message, title=title, border_style=style, expand=expand))

        # Log to file as plain text
        plain_message = f"{title}: {message}" if title else message
        self.logger.info(f"[PANEL] {plain_message}", extra={"markup": False})

    def section(self, title: str, style: str = "bold cyan"):
        """Log a section header"""
        separator = "=" * 80
        self.panel(f"[{style}]{title}[/{style}]", title="", style=style.split()[-1])
        self.logger.info(f"\n{separator}\n{title}\n{separator}", extra={"markup": False})

    def websocket_event(self, event_type: str, data: dict):
        """Log WebSocket events"""
        self.info(f"📡 WebSocket Event: {event_type} | Data: {data}")

    def agent_event(self, agent_id: str, event_type: str, message: str):
        """Log agent-specific events"""
        self.info(f"🤖 Agent-{agent_id} | {event_type}: {message}")

    def chat_event(self, orchestrator_id: str, message: str, sender: str = "orchestrator"):
        """Log chat interaction events"""
        truncated_msg = message[:100] + "..." if len(message) > 100 else message
        self.info(f"💬 Chat [{orchestrator_id}] {sender.upper()}: {truncated_msg}")

    def http_request(self, method: str, path: str, status: int = None):
        """Log HTTP requests"""
        status_text = f"[{status}]" if status else ""
        self.info(f"🌐 {method} {path} {status_text}")

    def startup(self, config: dict):
        """Log startup information"""
        self.section("🚀 ORCHESTRATOR BACKEND STARTING", "bold cyan")
        for key, value in config.items():
            self.info(f"  {key}: {value}")

    def shutdown(self):
        """Log shutdown"""
        self.section("👋 ORCHESTRATOR BACKEND SHUTTING DOWN", "bold yellow")


# Global logger instance
logger = OrchestratorLogger()


def get_logger() -> OrchestratorLogger:
    """Get the global logger instance"""
    return logger
