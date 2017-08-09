import collections
import logging
from urllib.parse import urljoin

import celery
from django.apps import apps
from django.utils.functional import cached_property

from .. import settings

logger = logging.getLogger(__name__)

__all__ = ['sync_pras']


class PRASSync(object):
    managed_tags = {'unit', 'college', 'pph', 'bodleian'}

    def __init__(self):
        self.current_organizations = []
        self.current_organizations_by_id = collections.defaultdict(dict)

    @cached_property
    def session(self):
        return apps.get_app_config('idm_integration').session

    def __call__(self):
        self.load_current_organizations()


        response = self.session.get(settings.PRAS_URL, headers={'Accept': 'application/json'})
        response.raise_for_status()

        print(list(self.current_organizations_by_id['pras:division']))

        for organization in self.get_organizations(response.json()):
            print(organization)
            try:
                existing = self.current_organizations_by_id[organization['code_type']][organization['code']]
            except KeyError:
                response = self.session.post(urljoin(settings.IDM_CORE_API_URL, 'organization/'), json={
                    'label': organization['name'],
                    'managed': True,
                    'identifiers': [{
                        'type': organization['code_type'],
                        'value': organization['code'],
                    }],
                    'tags': sorted(organization['tags']),
                })
                print(response.content)
                response.raise_for_status()
                logger.info("Created organization for %s (%s)",
                            organization['code'], organization['name'])

            else:
                existing_tags = set(existing['tags']) & self.managed_tags
                if existing['short_label'] != organization['name'] \
                        or existing['label'] != organization['full_name']\
                        or existing_tags != organization['tags']:
                    new_tags = (set(existing['tags']) - self.managed_tags) | organization['tags']
                    self.session.put(existing['url'], {
                        'label': organization['full_name'],
                        'short_label': organization['name'],
                        'tags': sorted(new_tags),
                    }).raise_for_status()
                    logger.info("Updated label for %s from '%s' to '%s'",
                                existing['id'], existing['label'], organization['full_name'])

    def load_current_organizations(self):
        url = urljoin(settings.IDM_CORE_API_URL, 'organization/')
        while True:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            for org in data['results']:
                self.add_identifier_dict(org)
                self.current_organizations.append(org)
                for identifier in org['identifiers']:
                    self.current_organizations_by_id[identifier['type']][identifier['value']] = org
            if data.get('next'):
                url = urljoin(url, data['next'])
            else:
                break

    def add_identifier_dict(self, org):
        identifier_dict = {}
        for identifier in org['identifiers']:
            if identifier['type'] not in identifier_dict:
                identifier_dict[identifier['type']] = []
            identifier_dict[identifier['type']].append(identifier)
        org['ids'] = identifier_dict

    def get_organizations(self, data, division=None):
        tags = set()

        code = data.get('Level1EntityCode') or data.get('Level2EntityCode') or data.get('Level3EntityCode') or ''
        name = data.get('Level1EntityName') or data.get('Level2EntityName') or data.get('Level3EntityName') or ''
        full_name = data.get('Level1EntityFullName') or data.get('Level2EntityFullName') or data.get('Level3EntityFullName') or ''

        # Cross-copy if either name is missing
        full_name, name = full_name or name, name or full_name

        if len(code) == 2 and code[0].isnumeric():
            code_type = 'pras:division'
            division = code
            tags.add('division')
        elif len(code) == 2:
            code_type = 'finance'
        else:
            code_type = 'pras:department'

        if division != '0A':
            tags.add('unit')
        if name.endswith(' College') or name == 'Christ Church':
            tags.add('college')
        if code in ('SM', 'SQ', 'SR', 'ST', 'SV', 'SY'):
            tags.add('pph')
        if code == 'QB':
            tags.add('bodleian')

        if code:
            yield {
                'name': name.strip(),
                'full_name': full_name.strip(),
                'code': code.strip(),
                'code_type': code_type,
                'tags': tags,
            }

        for name in ('Level1Entities', 'Level2Entities', 'Level3Entities'):
            for entity in data.get(name, ()):
                yield from self.get_organizations(entity, division)


@celery.shared_task
def sync_pras():
    PRASSync()()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    sync_pras()