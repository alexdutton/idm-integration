import os

DEBUG = os.environ.get('DJANGO_DEBUG')

USE_TZ = True
TIME_ZONE = 'Europe/London'

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')
if not SECRET_KEY and DEBUG:
    SECRET_KEY = 'very secret key'

INSTALLED_APPS = [
    'idm_integration.apps.IDMIntegrationConfig',
]

DATABASES = {}

PRAS_URL = 'https://orgstr-bp.it.ox.ac.uk/api/OrganisationStructure'

IDM_CORE_API_URL = os.environ.get('IDM_CORE_API_URL')
