"""Slack integration service for self-healing notifications"""
import os
import httpx
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select


class SlackService:
    """Service for sending notifications to Slack"""

    def __init__(self):
        # Defaults from environment (fallback)
        self._env_webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
        self._env_channel = os.environ.get('SLACK_CHANNEL', '#network-alerts')

        # Database config cache
        self._db_config: Optional[Dict[str, Any]] = None
        self._config_loaded = False

    def load_config_from_db(self, db: Session) -> None:
        """Load Slack configuration from database"""
        try:
            from .models import SystemSettingsModel
            query = select(SystemSettingsModel).where(SystemSettingsModel.id == 1)
            result = db.execute(query)
            settings = result.scalar_one_or_none()

            if settings and settings.slack_enabled:
                self._db_config = {
                    'enabled': settings.slack_enabled,
                    'webhook_url': settings.slack_webhook_url,
                    'channel': settings.slack_channel or '#network-alerts',
                    'notify_alerts': settings.slack_notify_alerts,
                    'notify_actions': settings.slack_notify_actions,
                    'critical_only': settings.slack_notify_critical_only,
                }
            else:
                self._db_config = None
            self._config_loaded = True
        except Exception as e:
            print(f"⚠️ Could not load Slack config from DB: {e}")
            self._db_config = None

    @property
    def webhook_url(self) -> Optional[str]:
        """Get webhook URL (DB config takes precedence over env)"""
        if self._db_config and self._db_config.get('webhook_url'):
            return self._db_config['webhook_url']
        return self._env_webhook_url

    @property
    def channel(self) -> str:
        """Get channel (DB config takes precedence over env)"""
        if self._db_config and self._db_config.get('channel'):
            return self._db_config['channel']
        return self._env_channel

    @property
    def enabled(self) -> bool:
        """Check if Slack is enabled (DB config takes precedence)"""
        if self._db_config:
            return self._db_config.get('enabled', False) and bool(self._db_config.get('webhook_url'))
        return bool(self._env_webhook_url)

    @property
    def notify_alerts(self) -> bool:
        """Check if alert notifications are enabled"""
        if self._db_config:
            return self._db_config.get('notify_alerts', True)
        return True

    @property
    def notify_actions(self) -> bool:
        """Check if action notifications are enabled"""
        if self._db_config:
            return self._db_config.get('notify_actions', True)
        return True

    @property
    def critical_only(self) -> bool:
        """Check if only critical alerts should be notified"""
        if self._db_config:
            return self._db_config.get('critical_only', False)
        return False

    def is_enabled(self) -> bool:
        return self.enabled

    def get_status(self) -> Dict[str, Any]:
        """Get current Slack configuration status"""
        return {
            "enabled": self.enabled,
            "channel": self.channel if self.enabled else None,
            "notify_alerts": self.notify_alerts,
            "notify_actions": self.notify_actions,
            "critical_only": self.critical_only,
            "config_source": "database" if self._db_config else "environment" if self._env_webhook_url else "none",
            "message": "Slack integration active" if self.enabled else "Configure Slack in Settings to enable notifications"
        }

    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send a message to Slack"""
        if not self.enabled:
            print("⚠️ Slack not configured (no webhook URL set)")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=message,
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception as e:
            print(f"❌ Slack notification failed: {e}")
            return False

    async def notify_alert(
        self,
        node_id: str,
        alert_type: str,
        severity: str,
        description: str,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """Send alert notification to Slack"""
        if not self.notify_alerts:
            return False

        if self.critical_only and severity.lower() != "critical":
            return False

        emoji = "🔴" if severity == "critical" else "🟡" if severity == "warning" else "ℹ️"
        color = "#dc2626" if severity == "critical" else "#f59e0b" if severity == "warning" else "#3b82f6"

        message = {
            "channel": self.channel,
            "attachments": [
                {
                    "color": color,
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": f"{emoji} Cable Network Alert - {severity.upper()}",
                                "emoji": True
                            }
                        },
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Node:*\n{node_id}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Alert Type:*\n{alert_type.replace('_', ' ').title()}"
                                }
                            ]
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Description:*\n{description}"
                            }
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"⏰ {(timestamp or datetime.now()).strftime('%Y-%m-%d %H:%M:%S UTC')}"
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        return await self.send_message(message)

    async def notify_self_healing_action(
        self,
        node_id: str,
        action_type: str,
        status: str,
        alert_id: Optional[str] = None,
        effectiveness_score: Optional[float] = None,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """Send self-healing action notification to Slack"""
        if not self.notify_actions:
            return False

        status_emoji = {
            "PENDING": "⏳",
            "IN_PROGRESS": "🔄",
            "COMPLETED": "✅",
            "FAILED": "❌"
        }
        emoji = status_emoji.get(status.upper(), "🔧")

        color = "#22c55e" if status.upper() == "COMPLETED" else "#dc2626" if status.upper() == "FAILED" else "#3b82f6"

        fields = [
            {
                "type": "mrkdwn",
                "text": f"*Node:*\n{node_id}"
            },
            {
                "type": "mrkdwn",
                "text": f"*Action:*\n{action_type.replace('_', ' ').title()}"
            },
            {
                "type": "mrkdwn",
                "text": f"*Status:*\n{status.upper()}"
            }
        ]

        if effectiveness_score:
            fields.append({
                "type": "mrkdwn",
                "text": f"*Effectiveness:*\n{effectiveness_score:.1f}%"
            })

        message = {
            "channel": self.channel,
            "attachments": [
                {
                    "color": color,
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": f"{emoji} Auto-Resolution Action - {status.upper()}",
                                "emoji": True
                            }
                        },
                        {
                            "type": "section",
                            "fields": fields
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"⏰ {(timestamp or datetime.now()).strftime('%Y-%m-%d %H:%M:%S UTC')}"
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        if alert_id:
            message["attachments"][0]["blocks"].insert(2, {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"🔗 Related Alert: `{alert_id}`"
                    }
                ]
            })

        return await self.send_message(message)

    async def notify_sdn_command(
        self,
        node_id: str,
        command_type: str,
        parameters: Dict[str, Any],
        simulated: bool = True
    ) -> bool:
        """Notify about SDN command (simulated for demo)"""
        message = {
            "channel": self.channel,
            "attachments": [
                {
                    "color": "#8b5cf6",
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": f"🌐 Network Command {'(Simulated)' if simulated else ''}",
                                "emoji": True
                            }
                        },
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Node:*\n{node_id}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Command:*\n{command_type.replace('_', ' ').title()}"
                                }
                            ]
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Parameters:*\n```{parameters}```"
                            }
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        return await self.send_message(message)


# Singleton instance
slack_service = SlackService()
