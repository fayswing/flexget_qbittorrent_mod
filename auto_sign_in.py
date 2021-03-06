from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from datetime import datetime

from flexget import plugin
from flexget.entry import Entry
from flexget.event import event

from .ptsites.executor import Executor
from .ptsites.utils.details_report import DetailsReport


class PluginAutoSignIn:
    schema = {
        'type': 'object',
        'properties': {
            'user-agent': {'type': 'string'},
            'command_executor': {'type': 'string'},
            'max_workers': {'type': 'integer'},
            'aipocr': {
                'type': 'object',
                'properties': {
                    'app_id': {'type': 'string'},
                    'api_key': {'type': 'string'},
                    'secret_key': {'type': 'string'}
                },
                'additionalProperties': False
            },
            'sites': {
                'type': 'object',
                'properties': {
                }
            }
        },
        'additionalProperties': False
    }

    def prepare_config(self, config):
        config.setdefault('user-agent', '')
        config.setdefault('command_executor', '')
        config.setdefault('max_workers', {})
        config.setdefault('aipocr', {})
        config.setdefault('sites', {})
        return config

    def on_task_input(self, task, config):
        config = self.prepare_config(config)
        sites = config.get('sites')

        entries = []

        for site_name, site_config in sites.items():
            if isinstance(site_config, list):
                for sub_site_config in site_config:
                    entry = self.build_sign_in_entry(site_name, sub_site_config, config)
                    entry['class_name'] = site_name
                    entries.append(entry)
            else:
                entry = self.build_sign_in_entry(site_name, site_config, config)
                entries.append(entry)
        return entries

    def on_task_output(self, task, config):
        max_workers = config.get('max_workers', 1)
        date_now = str(datetime.now().date())
        for entry in task.all_entries:
            if date_now not in entry['title']:
                entry.reject('{} out of date!'.format(entry['title']))
        if max_workers == 1:
            for entry in task.accepted:
                Executor.sign_in(entry, config)
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as t:
                all_task = [t.submit(Executor.sign_in, entry, config) for entry in task.accepted]
                wait(all_task, return_when=ALL_COMPLETED)
        DetailsReport().build(task)

    def build_sign_in_entry(self, site_name, site_config, config):
        entry = Entry(
            title='{} {}'.format(site_name, datetime.now().date()),
            url=''
        )
        entry['site_name'] = site_name
        entry['site_config'] = site_config
        Executor.build_sign_in_entry(entry, config)
        return entry


@event('plugin.register')
def register_plugin():
    plugin.register(PluginAutoSignIn, 'auto_sign_in', api_ver=2)
