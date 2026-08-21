from typing import TYPE_CHECKING, Generic, TypeVar

from flask import Flask
from flask_mail import Mail, Message
from vintasend.app_settings import NotificationSettings
from vintasend.constants import NotificationTypes
from vintasend.services.dataclasses import Notification, OneOffNotification
from vintasend.services.notification_adapters.base import BaseNotificationAdapter
from vintasend.services.notification_backends.base import BaseNotificationBackend
from vintasend.services.notification_template_renderers.base_templated_email_renderer import (
    BaseTemplatedEmailRenderer,
)


if TYPE_CHECKING:
    from vintasend.services.dataclasses import NotificationContextDict


B = TypeVar("B", bound=BaseNotificationBackend)
T = TypeVar("T", bound=BaseTemplatedEmailRenderer)


class FlaskMailNotificationAdapter(Generic[B, T], BaseNotificationAdapter[B, T]):  # noqa: UP046
    notification_type = NotificationTypes.EMAIL
    mail: Mail
    flask_app: Flask

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        flask_app = kwargs.get("flask_app")
        if not isinstance(flask_app, Flask):
            raise ValueError(
                "FlaskMailNotificationAdapter requires a `flask_app` keyword argument "
                "holding the Flask application."
            )
        self.flask_app = flask_app
        self.mail = Mail(self.flask_app)

    def send(
        self,
        notification: "Notification | OneOffNotification",
        context: "NotificationContextDict",
    ) -> None:
        """
        Send the notification to the user through email.

        :param notification: The notification to send (regular or one-off).
        :param context: The context to render the notification templates.
        """
        notification_settings = NotificationSettings()

        # flask-mail types a recipient as either an address or a (name, address) pair, so the
        # lists have to be widened to match or the invariant list[str] is rejected.
        to: list[str | tuple[str, str]] = [self._get_recipient_email(notification)]
        bcc: list[str | tuple[str, str]] = list(
            notification_settings.NOTIFICATION_DEFAULT_BCC_EMAILS
        )

        context_with_base_url: "NotificationContextDict" = context.copy()
        context_with_base_url["base_url"] = (
            f"{notification_settings.NOTIFICATION_DEFAULT_BASE_URL_PROTOCOL}://{notification_settings.NOTIFICATION_DEFAULT_BASE_URL_DOMAIN}"
        )

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

    def _get_recipient_email(self, notification: "Notification | OneOffNotification") -> str:
        """Resolve the destination address for either notification flavour.

        A one-off notification carries the address on itself; a regular one only knows the
        user, so the backend has to look it up.
        """
        if isinstance(notification, OneOffNotification):
            return notification.email_or_phone
        return self.backend.get_user_email_from_notification(notification.id)
