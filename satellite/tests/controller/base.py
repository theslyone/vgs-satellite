from unittest.mock import Mock, patch

import pytest

from snapshottest.unittest import TestCase
from tornado.testing import AsyncHTTPTestCase

from satellite.web_application import WebApplication


@pytest.mark.usefixtures('snapshot_pytest_unitest_bridge')
class BaseHandlerTestCase(AsyncHTTPTestCase, TestCase):
    def setUp(self):
        # Patches below must be before super().setUp()-call
        self.master = Mock()
        create_proxy_patch = patch(
            'satellite.web_application.create_proxy',
            Mock(return_value=self.master),
        )
        create_proxy_patch.start()
        self.addCleanup(create_proxy_patch.stop)

        super().setUp()

    def get_app(self):
        return WebApplication()
