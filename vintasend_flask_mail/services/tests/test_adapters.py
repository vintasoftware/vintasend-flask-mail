import uuid
from unittest import TestCase

import pytest
from flask import Flask
from vintasend.constants import NotificationStatus, NotificationTypes
from vintasend.exceptions import (
    NotificationTemplateRenderingError,
)
from vintasend.services.dataclasses import Notification
from vintasend.services.notification_backends.stubs.fake_backend import (
    FakeFileBackend,
)

from vintasend_flask_mail.services.notification_adapters.flask_mail import (
    FlaskMailNotificationAdapter,
)


class FlaskMailNotificationAdapterTestCase(TestCase):
    def setup_method(self, method) -> None:
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, MAIL_DEFAULT_SENDER="foo@example.com")
        super().setUp()

    def teardown_method(self, method) -> None:
        FakeFileBackend(database_file_name="flask-mail-adapter-test-notifications.json").clear()
    
    def teardown_class(self) -> None:
        FakeFileBackend(database_file_name="flask-mail-adapter-test-notifications.json").clear()

    def create_notification(self):
        return Notification(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            notification_type=NotificationTypes.EMAIL.value,
            title="Test Notification",
            body_template="Test Body",
            context_name="test_context",
            context_kwargs={"test": "test"},
            send_after=None,
            subject_template="Test Subject",
            preheader_template="Test Preheader",
            status=NotificationStatus.PENDING_SEND.value,
        )

    def create_notification_context(self):
        return {"foo": "bar"}

    @pytest.mark.asyncio
    def test_send_notification(self):
        notification = self.create_notification()
        context = self.create_notification_context()

        backend = FakeFileBackend(database_file_name="flask-mail-adapter-test-notifications.json")
        backend.notifications.append(notification)
        backend._store_notifications()

        adapter = FlaskMailNotificationAdapter(
            "vintasend.services.notification_template_renderers.stubs.fake_templated_email_renderer.FakeTemplateRenderer",
            "vintasend.services.notification_backends.stubs.fake_backend.FakeFileBackend",
            backend_kwargs={"database_file_name": "flask-mail-adapter-test-notifications.json"},
            flask_app=self.app,
        )

        with adapter.mail.record_messages() as outbox:
            adapter.send(notification, context)

        assert len(outbox) == 1
        email = outbox[0]
        assert email.subject == notification.subject_template
        assert email.body == notification.body_template
        assert email.recipients == ["testemail@example.com"]  # This is the email that the FakeFileBackend returns
        assert email.sender == "foo@example.com"  # This is the email that the FakeFileBackend returns

    @pytest.mark.asyncio
    async def test_send_notification_with_render_error(self):
        notification = self.create_notification()
        context = self.create_notification_context()

        backend = FakeFileBackend(database_file_name="flask-mail-adapter-test-notifications.json")
        backend.notifications.append(notification)
        backend._store_notifications()

        adapter = FlaskMailNotificationAdapter(
            "vintasend.services.notification_template_renderers.stubs.fake_templated_email_renderer.FakeTemplateRendererWithException",
            "vintasend.services.notification_backends.stubs.fake_backend.FakeFileBackend",
            backend_kwargs={"database_file_name": "flask-mail-adapter-test-notifications.json"},
            flask_app=self.app,
        )
        with adapter.mail.record_messages() as outbox:
            with pytest.raises(NotificationTemplateRenderingError):
                adapter.send(notification, context)

        assert len(outbox) == 0
