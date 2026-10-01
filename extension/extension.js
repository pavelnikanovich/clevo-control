// SPDX-License-Identifier: GPL-2.0-or-later
//
// The firmware "quiet" performance profile in GNOME's quick settings.
//
// GNOME's power mode menu knows three profiles. power-profiles-daemon treats
// the firmware profile "quiet" as Power Saver, so quiet is written behind the
// daemon's back: the daemon then reports Power Saver and stays consistent. This
// extension adds a "Quiet" entry to the shell's Power Mode menu and shows which
// entry matches the real firmware profile.
//
// The menu is extended by overriding two private methods of the shell's power
// profile toggle. When that is not possible, or power-profiles-daemon is not
// running (the shell then hides its toggle), a separate Quiet Mode toggle is
// shown instead.

import GObject from 'gi://GObject';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import {Extension, InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';
import {QuickToggle, SystemIndicator} from 'resource:///org/gnome/shell/ui/quickSettings.js';

import {PowerProfilesClient, ProfileController} from './controller.js';

const QUIET_ICON = 'power-profile-power-saver-symbolic';

const QuietToggle = GObject.registerClass(
class QuietToggle extends QuickToggle {
    constructor(controller) {
        super({
            title: 'Quiet Mode',
            iconName: QUIET_ICON,
            toggleMode: false,
        });

        this._controller = controller;
        const unwatch = controller.watch(() => this._sync());
        this.connect('destroy', unwatch);
        this.connect('clicked', () => {
            if (controller.quiet)
                controller.leaveQuiet();
            else
                controller.enterQuiet();
        });
        this._sync();
    }

    _sync() {
        this.visible = this._controller.available;
        this.checked = this._controller.quiet;
    }
});

const QuietIndicator = GObject.registerClass(
class QuietIndicator extends SystemIndicator {
    constructor(controller) {
        super();
        this.quickSettingsItems.push(new QuietToggle(controller));
    }

    destroy() {
        this.quickSettingsItems.forEach(item => item.destroy());
        super.destroy();
    }
});

/** The shell's power profile toggle, or null if it does not look as expected. */
function findPowerToggle() {
    const toggle = Main.panel.statusArea.quickSettings
        ?._powerProfiles?.quickSettingsItems?.[0];

    if (toggle?._profileSection && toggle._profileItems instanceof Map &&
        typeof toggle._syncProfiles === 'function' &&
        typeof toggle._sync === 'function' && toggle._proxy)
        return toggle;
    return null;
}

/** Adds "Quiet" to the shell's Power Mode menu. */
class PowerMenuIntegration {
    constructor(toggle, controller) {
        this._toggle = toggle;
        this._controller = controller;
        this._quietItem = null;
        // [item, handler id] for every handler connected to an item of the shell.
        this._handlers = [];
        this._injections = new InjectionManager();

        const integration = this;
        const proto = Object.getPrototypeOf(toggle);
        // The shell rebuilds its items here and destroys the old ones.
        this._injections.overrideMethod(proto, '_syncProfiles', original => function (...args) {
            integration._forgetItems();
            original.apply(this, args);
            integration._addItems();
        });
        this._injections.overrideMethod(proto, '_sync', original => function (...args) {
            original.apply(this, args);
            integration._syncItems();
        });

        this._unwatch = controller.watch(() => this._toggle._sync());
        // Without the daemon's profile list the shell has not built its menu
        // yet; it calls _syncProfiles() itself once the list arrives.
        if (this._toggle._proxy.Profiles)
            this._toggle._syncProfiles();
        this._toggle._sync();
    }

    _forgetItems() {
        this._handlers = [];
        this._quietItem = null;
    }

    _addItems() {
        if (!this._controller.available)
            return;

        // The shell asks the daemon for the chosen mode. The firmware profile
        // is written as well: see ProfileController.leaveQuietFor().
        for (const [mode, item] of this._toggle._profileItems) {
            const id = item.connect('activate', () => this._controller.leaveQuietFor(mode));
            this._handlers.push([item, id]);
        }

        this._quietItem = new PopupMenu.PopupImageMenuItem('Quiet', QUIET_ICON);
        this._quietItem.connect('activate', () => this._controller.enterQuiet());
        this._toggle._profileSection.addMenuItem(this._quietItem);
    }

    _syncItems() {
        if (!this._quietItem) {
            // The profile device appeared after the menu was built.
            if (!this._controller.available || this._toggle._profileItems.size === 0)
                return;
            this._toggle._syncProfiles();
            if (!this._quietItem)
                return;
        }

        const quiet = this._controller.quiet;
        this._quietItem.setOrnament(quiet
            ? PopupMenu.Ornament.CHECK
            : PopupMenu.Ornament.NONE);
        if (quiet) {
            for (const item of this._toggle._profileItems.values())
                item.setOrnament(PopupMenu.Ornament.NONE);
            this._toggle.set({subtitle: 'Quiet'});
        }
    }

    destroy() {
        this._unwatch();
        this._injections.clear();

        for (const [item, id] of this._handlers)
            item.disconnect(id);
        this._quietItem?.destroy();
        this._forgetItems();

        // Back to the shell's own subtitle and check marks.
        this._toggle._sync();
    }
}

export default class ClevoControlExtension extends Extension {
    enable() {
        this._controller = new ProfileController({
            daemon: new PowerProfilesClient(),
            onError: message => Main.notifyError('Clevo Control', message),
        });
        this._powerMenu = null;
        this._indicator = null;

        this._toggle = findPowerToggle();
        if (this._toggle) {
            this._ownerChangedId = this._toggle._proxy.connect(
                'notify::g-name-owner', () => this._chooseInterface());
        } else {
            console.warn(`${this.uuid}: the Power Mode menu cannot be extended`);
        }

        // Before the menu opens, the profile may have changed without a
        // notification (device re-created by a module reload).
        const menu = Main.panel.statusArea.quickSettings.menu;
        this._menuOpenId = menu.connect('open-state-changed', (_menu, open) => {
            if (open)
                this._controller.refresh();
        });

        this._chooseInterface();
        this._controller.refresh();
    }

    /** The menu entry while the shell shows its toggle, our own toggle otherwise. */
    _chooseInterface() {
        const useMenu = this._toggle !== null && this._toggle._proxy.g_name_owner !== null;

        if (useMenu && !this._powerMenu) {
            this._indicator?.destroy();
            this._indicator = null;
            try {
                this._powerMenu = new PowerMenuIntegration(this._toggle, this._controller);
                return;
            } catch (e) {
                console.warn(`${this.uuid}: the Power Mode menu was not extended: ${e.message}`);
                this._powerMenu = null;
            }
        } else if (useMenu) {
            return;
        }

        this._powerMenu?.destroy();
        this._powerMenu = null;
        if (!this._indicator) {
            this._indicator = new QuietIndicator(this._controller);
            Main.panel.statusArea.quickSettings.addExternalIndicator(this._indicator);
        }
    }

    disable() {
        Main.panel.statusArea.quickSettings.menu.disconnect(this._menuOpenId);
        this._menuOpenId = null;
        if (this._toggle) {
            this._toggle._proxy.disconnect(this._ownerChangedId);
            this._ownerChangedId = null;
        }

        this._powerMenu?.destroy();
        this._powerMenu = null;
        this._indicator?.destroy();
        this._indicator = null;
        this._toggle = null;

        this._controller.destroy();
        this._controller = null;
    }
}
