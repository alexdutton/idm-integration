import os

import requests
import requests_negotiate
from django.apps import AppConfig


class IDMIntegrationConfig(AppConfig):
    name = 'idm_integration'

    def ready(self):
        self.session = requests.Session()
        self.session.auth = requests_negotiate.HTTPNegotiateAuth(
            negotiate_client_name=os.environ.get('CLIENT_PRINCIPAL_NAME'))

