from typing import TYPE_CHECKING, Generic, TypeVar

from flask import Flask
from flask_mail import Mail, Message
from vintasend.app_settings import NotificationSettings
from vintasend.constants import NotificationTypes
from vintasend.services.dataclasses import Notification
from vintasend.services.notification_adapters.base import BaseNotificationAdapter
from vintasend.services.notification_backends.base import BaseNotificationBackend
from vintasend.services.notification_template_renderers.base_templated_email_renderer import (
    BaseTemplatedEmailRenderer,
)


if TYPE_CHECKING:
    from vintasend.services.notification_service import NotificationContextDict


B = TypeVar("B", bound=BaseNotificationBackend)
T = TypeVar("T", bound=BaseTemplatedEmailRenderer)

class FlaskMailNotificationAdapter(Generic[B, T], BaseNotificationAdapter[B, T]):
    notification_type = NotificationTypes.EMAIL
    mail: Mail
    flask_app: Flask

    def __init__(
        self, *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.flask_app = kwargs.get("flask_app")
        self.mail = Mail(self.flask_app)

    def send(
        self,
        notification: Notification,
        context: "NotificationContextDict",
    ) -> None:
        """
        Send the notification to the user through email.

        :param notification: The notification to send.
        :param context: The context to render the notification templates.
        """
        notification_settings = NotificationSettings()

        user_email = self.backend.get_user_email_from_notification(notification.id)
        to = [user_email]
        bcc = [email for email in notification_settings.NOTIFICATION_DEFAULT_BCC_EMAILS] or []

        context_with_base_url: "NotificationContextDict" = context.copy()
        context_with_base_url["base_url"] = f"{notification_settings.NOTIFICATION_DEFAULT_BASE_URL_PROTOCOL}://{notification_settings.NOTIFICATION_DEFAULT_BASE_URL_DOMAIN}"

        template = self.template_renderer.render(notification, context_with_base_url)
        with self.flask_app.app_context():
            message = Message(
                subject=template.subject.strip(),
                recipients=to,
                body=template.body,
                html=template.body,
                bcc=bcc,
            )
            self.mail.send(message)
