// SPDX-License-Identifier: GPL-2.0-or-later
//
// Stand-in for resource:///org/gnome/shell/ui/main.js: a power profile toggle
// that behaves like the one in GNOME Shell 50 (ui/status/powerProfiles.js) as
// far as the extension can tell, and the quick settings that hold it.

import {Ornament, PopupImageMenuItem, PopupMenuSection} from './popupMenu.js';

const NAMES = {'performance': 'Performance', 'balanced': 'Balanced', 'power-saver': 'Power Saver'};

/** Minimal signal support, with a count of what is still connected. */
export class Signals {
    constructor() {
        this.handlers = new Map();
        this._nextId = 1;
    }

    connect(signal, callback) {
        this.handlers.set(this._nextId, [signal, callback]);
        return this._nextId++;
    }

    disconnect(id) {
        if (!this.handlers.delete(id))
            throw new Error(`disconnect of unknown handler ${id}`);
    }

    emit(signal, ...args) {
        for (const [name, callback] of [...this.handlers.values()]) {
            if (name === signal)
                callback(this, ...args);
        }
    }
}

class Proxy extends Signals {
    constructor() {
        super();
        this.g_name_owner = ':1.1';
        this.ActiveProfile = 'balanced';
        this.Profiles = ['power-saver', 'balanced', 'performance']
            .map(profile => ({Profile: {unpack: () => profile}}));
    }

    setOwner(owner) {
        this.g_name_owner = owner;
        this.emit('notify::g-name-owner');
    }
}

export class PowerProfilesToggle extends Signals {
    constructor() {
        super();
        this._profileItems = new Map();
        this._proxy = new Proxy();
        this._profileSection = new PopupMenuSection();
        this.visible = false;
        this.subtitle = null;
    }

    set(properties) {
        Object.assign(this, properties);
    }

    _syncProfiles() {
        this._profileSection.removeAll();
        this._profileItems.clear();
        for (const {Profile} of [...this._proxy.Profiles].reverse()) {
            const profile = Profile.unpack();
            const item = new PopupImageMenuItem(NAMES[profile], '');
            item.connect('activate', () => (this._proxy.ActiveProfile = profile));
            this._profileItems.set(profile, item);
            this._profileSection.addMenuItem(item);
        }
    }

    _sync() {
        const visible = this._proxy.g_name_owner !== null;
        if (visible !== this.visible) {
            this.visible = visible;
            this.emit('notify::visible');
        }
        if (!this.visible)
            return;

        const active = this._proxy.ActiveProfile;
        for (const [profile, item] of this._profileItems) {
            item.setOrnament(profile === active ? Ornament.CHECK : Ornament.NONE);
        }
        this.set({subtitle: NAMES[active]});
    }

    /** The daemon went away or came back; the shell re-syncs on its own signal. */
    setDaemonOwner(owner) {
        this._proxy.setOwner(owner);
        this._sync();
    }
}

export const toggle = new PowerProfilesToggle();
// What the shell has done by the time an extension is enabled.
toggle._syncProfiles();
toggle._sync();

export const externalIndicators = [];
export const errors = [];
export const quickSettingsMenu = new Signals();

export const panel = {
    statusArea: {
        quickSettings: {
            _powerProfiles: {quickSettingsItems: [toggle]},
            menu: quickSettingsMenu,
            addExternalIndicator(indicator) {
                externalIndicators.push(indicator);
            },
        },
    },
};

export function notifyError(_title, message) {
    errors.push(message);
}
