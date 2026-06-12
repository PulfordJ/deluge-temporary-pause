import logging
import time

from twisted.internet import reactor

import deluge.component as component
import deluge.configmanager
from deluge.core.rpcserver import export
from deluge.plugins.pluginbase import CorePluginBase

log = logging.getLogger(__name__)

DEFAULT_PREFS = {
    'global_pause_until': 0.0,
    'torrent_pauses': {},
}


class Core(CorePluginBase):
    def enable(self):
        self.config = deluge.configmanager.ConfigManager(
            'temporarypause.conf', DEFAULT_PREFS
        )
        self._global_timer = None
        self._torrent_timers = {}
        self._restore_pauses()

    def disable(self):
        self._cancel_global_timer()
        for torrent_id in list(self._torrent_timers):
            self._cancel_torrent_timer(torrent_id)

    def update(self):
        pass

    # --- internal helpers ---

    def _restore_pauses(self):
        now = time.time()

        global_until = self.config['global_pause_until']
        if global_until > now:
            component.get('Core').pause_session()
            self._global_timer = reactor.callLater(
                global_until - now, self._on_global_resume
            )
        elif global_until > 0:
            self.config['global_pause_until'] = 0.0
            self.config.save()

        expired = []
        torrent_pauses = dict(self.config['torrent_pauses'])
        for torrent_id, pause_until in torrent_pauses.items():
            if pause_until > now:
                self._pause_torrent_now(torrent_id)
                self._torrent_timers[torrent_id] = reactor.callLater(
                    pause_until - now, self._on_torrent_resume, torrent_id
                )
            else:
                expired.append(torrent_id)

        if expired:
            for tid in expired:
                del torrent_pauses[tid]
            self.config['torrent_pauses'] = torrent_pauses
            self.config.save()

    def _cancel_global_timer(self):
        if self._global_timer and self._global_timer.active():
            self._global_timer.cancel()
        self._global_timer = None

    def _cancel_torrent_timer(self, torrent_id):
        timer = self._torrent_timers.pop(torrent_id, None)
        if timer and timer.active():
            timer.cancel()

    def _pause_torrent_now(self, torrent_id):
        tm = component.get('TorrentManager')
        if torrent_id in tm.torrents:
            tm.torrents[torrent_id].pause()

    def _on_global_resume(self):
        self._global_timer = None
        self.config['global_pause_until'] = 0.0
        self.config.save()
        component.get('Core').resume_session()
        log.info('TemporaryPause: global pause expired, resuming session')

    def _on_torrent_resume(self, torrent_id):
        self._torrent_timers.pop(torrent_id, None)
        torrent_pauses = dict(self.config['torrent_pauses'])
        torrent_pauses.pop(torrent_id, None)
        self.config['torrent_pauses'] = torrent_pauses
        self.config.save()

        tm = component.get('TorrentManager')
        if torrent_id in tm.torrents:
            tm.torrents[torrent_id].resume()
        log.info('TemporaryPause: torrent %s pause expired, resuming', torrent_id)

    # --- exported RPC methods ---

    @export
    def pause_session(self, duration):
        """Pause the entire session for `duration` seconds."""
        self._cancel_global_timer()
        pause_until = time.time() + duration
        self.config['global_pause_until'] = pause_until
        self.config.save()
        component.get('Core').pause_session()
        self._global_timer = reactor.callLater(duration, self._on_global_resume)
        log.info('TemporaryPause: session paused for %.0f seconds', duration)
        return True

    @export
    def cancel_session_pause(self):
        """Cancel an active global session pause and resume immediately."""
        self._cancel_global_timer()
        self.config['global_pause_until'] = 0.0
        self.config.save()
        component.get('Core').resume_session()
        log.info('TemporaryPause: global pause cancelled')
        return True

    @export
    def pause_torrent(self, torrent_id, duration):
        """Pause a single torrent for `duration` seconds."""
        self._cancel_torrent_timer(torrent_id)
        pause_until = time.time() + duration
        torrent_pauses = dict(self.config['torrent_pauses'])
        torrent_pauses[torrent_id] = pause_until
        self.config['torrent_pauses'] = torrent_pauses
        self.config.save()
        self._pause_torrent_now(torrent_id)
        self._torrent_timers[torrent_id] = reactor.callLater(
            duration, self._on_torrent_resume, torrent_id
        )
        log.info('TemporaryPause: torrent %s paused for %.0f seconds', torrent_id, duration)
        return True

    @export
    def cancel_torrent_pause(self, torrent_id):
        """Cancel an active per-torrent pause and resume it immediately."""
        self._cancel_torrent_timer(torrent_id)
        torrent_pauses = dict(self.config['torrent_pauses'])
        torrent_pauses.pop(torrent_id, None)
        self.config['torrent_pauses'] = torrent_pauses
        self.config.save()
        tm = component.get('TorrentManager')
        if torrent_id in tm.torrents:
            tm.torrents[torrent_id].resume()
        log.info('TemporaryPause: torrent %s pause cancelled', torrent_id)
        return True

    @export
    def get_status(self):
        """Return current pause state for session and all paused torrents."""
        now = time.time()
        global_until = self.config['global_pause_until']
        torrent_pauses = dict(self.config['torrent_pauses'])

        active_torrent_pauses = {
            tid: {
                'until': until,
                'remaining': max(0.0, until - now),
            }
            for tid, until in torrent_pauses.items()
            if until > now
        }

        return {
            'global_paused': global_until > now,
            'global_pause_until': global_until,
            'global_remaining': max(0.0, global_until - now) if global_until > now else 0.0,
            'torrent_pauses': active_torrent_pauses,
        }
