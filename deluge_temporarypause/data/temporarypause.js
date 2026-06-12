/**
 * temporarypause.js
 *   Web UI for the TemporaryPause plugin.
 *
 * Adds:
 *   - A Preferences page with global pause controls and status
 *   - A right-click context menu "Temporary Pause" submenu on torrents
 */

Ext.ns('Deluge.ux.preferences');

// --- helpers ---

var TP_DURATIONS = [
    { label: '2 Hours',  seconds: 7200   },
    { label: '4 Hours',  seconds: 14400  },
    { label: '8 Hours',  seconds: 28800  },
    { label: '16 Hours', seconds: 57600  },
    { label: '1 Day',    seconds: 86400  },
    { label: '2 Days',   seconds: 172800 },
];

function tp_formatRemaining(seconds) {
    if (seconds <= 0) return 'none';
    var h = Math.floor(seconds / 3600);
    var m = Math.floor((seconds % 3600) / 60);
    var s = Math.floor(seconds % 60);
    if (h > 0) return h + 'h ' + m + 'm';
    if (m > 0) return m + 'm ' + s + 's';
    return s + 's';
}

// --- Preferences page ---

Deluge.ux.preferences.TemporaryPausePage = Ext.extend(Ext.Panel, {
    border: false,
    title: _('Temporary Pause'),
    header: false,
    layout: 'form',

    initComponent: function () {
        Deluge.ux.preferences.TemporaryPausePage.superclass.initComponent.call(this);

        // Status panel
        this.statusPanel = this.add({
            xtype: 'fieldset',
            title: _('Current Status'),
            autoHeight: true,
            border: true,
            style: 'margin-bottom: 10px;',
        });

        this.globalStatus = this.statusPanel.add({
            xtype: 'displayfield',
            fieldLabel: _('Global session'),
            value: _('Not paused'),
            style: 'font-weight: bold;',
        });

        this.cancelGlobalBtn = this.statusPanel.add({
            xtype: 'button',
            text: _('Cancel Global Pause'),
            hidden: true,
            handler: this.onCancelGlobal,
            scope: this,
        });

        // Global pause controls
        this.globalPanel = this.add({
            xtype: 'fieldset',
            title: _('Pause Entire Session'),
            autoHeight: true,
            border: true,
            style: 'margin-bottom: 10px;',
        });

        var buttons = [];
        Ext.each(TP_DURATIONS, function (d) {
            buttons.push({
                xtype: 'button',
                text: d.label,
                style: 'margin: 3px;',
                handler: (function (secs) {
                    return function () { this.onPauseSession(secs); };
                })(d.seconds),
                scope: this,
            });
        }, this);

        this.globalPanel.add({
            xtype: 'compositefield',
            hideLabel: true,
            items: buttons,
        });

        this.on('show', this.refreshStatus, this);
    },

    onPauseSession: function (duration) {
        deluge.client.temporarypause.pause_session(duration, {
            success: function () { this.refreshStatus(); },
            scope: this,
        });
    },

    onCancelGlobal: function () {
        deluge.client.temporarypause.cancel_session_pause({
            success: function () { this.refreshStatus(); },
            scope: this,
        });
    },

    refreshStatus: function () {
        deluge.client.temporarypause.get_status({
            success: function (status) {
                if (status.global_paused) {
                    this.globalStatus.setValue(
                        _('Paused &mdash; ') + tp_formatRemaining(status.global_remaining) + _(' remaining')
                    );
                    this.cancelGlobalBtn.show();
                } else {
                    this.globalStatus.setValue(_('Not paused'));
                    this.cancelGlobalBtn.hide();
                }
                this.doLayout();
            },
            scope: this,
        });
    },

    // Called by Preferences dialog when user clicks Apply/OK
    onApply: function () {},
    onOk: function () {},
});

// --- Context menu items for per-torrent pause ---

function tp_getSelectedIds() {
    return deluge.torrents.getSelectedIds();
}

function tp_buildTorrentPauseMenu() {
    var items = [];
    Ext.each(TP_DURATIONS, function (d) {
        items.push({
            text: d.label,
            handler: (function (secs) {
                return function () {
                    var ids = tp_getSelectedIds();
                    Ext.each(ids, function (id) {
                        deluge.client.temporarypause.pause_torrent(id, secs, {
                            success: function () {},
                        });
                    });
                };
            })(d.seconds),
        });
    });

    items.push('-');
    items.push({
        text: _('Cancel Temporary Pause'),
        handler: function () {
            var ids = tp_getSelectedIds();
            Ext.each(ids, function (id) {
                deluge.client.temporarypause.cancel_torrent_pause(id, {
                    success: function () {},
                });
            });
        },
    });

    return new Ext.menu.Menu({ items: items });
}

// --- Plugin registration ---

Deluge.plugins.TemporaryPausePlugin = Ext.extend(Deluge.Plugin, {
    name: 'TemporaryPause',

    onEnable: function () {
        this.prefsPage = deluge.preferences.addPage(
            new Deluge.ux.preferences.TemporaryPausePage()
        );

        // Add separator + submenu to torrent right-click menu
        this.menuSep = deluge.menus.torrent.addSeparator();
        this.torrentPauseMenu = tp_buildTorrentPauseMenu();
        this.menuItem = deluge.menus.torrent.add({
            text: _('Temporary Pause'),
            menu: this.torrentPauseMenu,
        });
    },

    onDisable: function () {
        deluge.preferences.removePage(this.prefsPage);
        if (this.menuItem) {
            deluge.menus.torrent.remove(this.menuItem);
            this.menuItem = null;
        }
        if (this.menuSep) {
            deluge.menus.torrent.remove(this.menuSep);
            this.menuSep = null;
        }
        if (this.torrentPauseMenu) {
            this.torrentPauseMenu.destroy();
            this.torrentPauseMenu = null;
        }
    },
});

Deluge.registerPlugin('TemporaryPause', Deluge.plugins.TemporaryPausePlugin);
