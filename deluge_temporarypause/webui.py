import logging

from deluge.plugins.pluginbase import WebPluginBase

from .common import get_resource

log = logging.getLogger(__name__)


class WebUI(WebPluginBase):
    scripts = [get_resource('temporarypause.js')]
    debug_scripts = scripts

    def enable(self):
        pass

    def disable(self):
        pass
