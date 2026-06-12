from setuptools import find_packages, setup

setup(
    name='TemporaryPause',
    version='0.1',
    description='Pause downloads/uploads globally or per-torrent for a fixed duration',
    author='John Pulford',
    packages=find_packages(),
    package_data={'deluge_temporarypause': ['data/*']},
    entry_points={
        'deluge.plugin.core': [
            'TemporaryPause = deluge_temporarypause:CorePlugin',
        ],
        'deluge.plugin.gtk3ui': [
            'TemporaryPause = deluge_temporarypause:GtkUIPlugin',
        ],
        'deluge.plugin.web': [
            'TemporaryPause = deluge_temporarypause:WebUIPlugin',
        ],
    },
)
