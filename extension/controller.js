// SPDX-License-Identifier: GPL-2.0-or-later
//
// Reads, watches and changes the firmware performance profile exposed by the
// clevo-control kernel module as a platform profile. No GNOME Shell imports
// here, so this file can be exercised with plain gjs (tests/extension).

import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

Gio._promisify(Gio.File.prototype, 'load_contents_async');
Gio._promisify(Gio.File.prototype, 'enumerate_children_async');
Gio._promisify(Gio.File.prototype, 'replace_contents_bytes_async', 'replace_contents_finish');
Gio._promisify(Gio.FileEnumerator.prototype, 'next_files_async');
Gio._promisify(Gio.DBusConnection.prototype, 'call');

export const QUIET = 'quiet';

const CLASS_DIR = '/sys/class/platform-profile';
const HANDLER_NAME = 'clevo';

const PPD_NAME = 'org.freedesktop.UPower.PowerProfiles';
const PPD_PATH = '/org/freedesktop/UPower/PowerProfiles';
const PPD_IFACE = 'org.freedesktop.UPower.PowerProfiles';

function isCancelled(error) {
    return error instanceof GLib.Error &&
        error.matches(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED);
}

/** The desktop power mode, as power-profiles-daemon sees it. */
export class PowerProfilesClient {
    async getActive(cancellable) {
        const reply = await Gio.DBus.system.call(
            PPD_NAME, PPD_PATH, 'org.freedesktop.DBus.Properties', 'Get',
            new GLib.Variant('(ss)', [PPD_IFACE, 'ActiveProfile']),
            new GLib.VariantType('(v)'), Gio.DBusCallFlags.NONE, -1, cancellable);
        const [value] = reply.deepUnpack();
        return value.deepUnpack();
    }

    async setActive(mode, cancellable) {
        await Gio.DBus.system.call(
            PPD_NAME, PPD_PATH, 'org.freedesktop.DBus.Properties', 'Set',
            new GLib.Variant('(ssv)', [PPD_IFACE, 'ActiveProfile', new GLib.Variant('s', mode)]),
            null, Gio.DBusCallFlags.NONE, -1, cancellable);
    }
}

export class ProfileController {
    /**
     * @param {object} params
     * @param {object} params.daemon - a PowerProfilesClient
     * @param {Function} params.onError - called with a message when the profile cannot be set
     * @param {string} [params.classDir] - platform-profile class directory
     */
    constructor({daemon, onError, classDir = CLASS_DIR}) {
        this._daemon = daemon;
        this._onError = onError;
        this._classDir = classDir;

        this._cancellable = new Gio.Cancellable();
        this._listeners = new Set();
        this._handler = null;
        this._monitor = null;
        this._profile = null;
        this._choices = [];
        // Desktop power mode to go back to when quiet is switched off.
        this._previous = 'balanced';
    }

    /** The firmware profile as last read, or null while the device is absent. */
    get profile() {
        return this._profile;
    }

    get available() {
        return this._profile !== null;
    }

    get quiet() {
        return this._profile === QUIET;
    }

    /** Calls back whenever the profile changed. Returns a function that stops it. */
    watch(callback) {
        this._listeners.add(callback);
        return () => this._listeners.delete(callback);
    }

    _setProfile(profile) {
        if (profile === this._profile)
            return;
        this._profile = profile;
        for (const callback of this._listeners)
            callback();
    }

    async _readText(path) {
        const [contents] = await Gio.File.new_for_path(path)
            .load_contents_async(this._cancellable);
        return new TextDecoder().decode(contents).trim();
    }

    /** Find the handler directory. Its index changes when the module is reloaded. */
    async _findHandler() {
        const dir = Gio.File.new_for_path(this._classDir);
        const enumerator = await dir.enumerate_children_async(
            'standard::name', Gio.FileQueryInfoFlags.NONE, GLib.PRIORITY_DEFAULT,
            this._cancellable);

        for (;;) {
            // eslint-disable-next-line no-await-in-loop
            const infos = await enumerator.next_files_async(
                16, GLib.PRIORITY_DEFAULT, this._cancellable);
            if (infos.length === 0)
                return null;

            for (const info of infos) {
                const path = `${this._classDir}/${info.get_name()}`;
                try {
                    // eslint-disable-next-line no-await-in-loop
                    if (await this._readText(`${path}/name`) === HANDLER_NAME)
                        return path;
                } catch (e) {
                    if (isCancelled(e))
                        throw e;
                }
            }
        }
    }

    _forgetHandler() {
        this._monitor?.cancel();
        this._monitor = null;
        this._handler = null;
        this._choices = [];
    }

    /**
     * Read the profile again. Also the way a handler that appeared, disappeared
     * or was re-created (module reload) is noticed.
     */
    refresh() {
        // One at a time: two concurrent runs would each create a file monitor.
        this._refreshing = (this._refreshing ?? Promise.resolve())
            .then(() => this._refresh());
        return this._refreshing;
    }

    async _refresh() {
        if (this._cancellable.is_cancelled())
            return;

        try {
            if (this._handler === null) {
                this._handler = await this._findHandler();
                if (this._handler === null) {
                    this._setProfile(null);
                    return;
                }
                this._choices = (await this._readText(`${this._handler}/choices`)).split(/\s+/);
                this._monitor = Gio.File.new_for_path(`${this._handler}/profile`)
                    .monitor_file(Gio.FileMonitorFlags.NONE, this._cancellable);
                this._monitor.connect('changed', () => this.refresh());
            }
            this._setProfile(await this._readText(`${this._handler}/profile`));
        } catch (e) {
            if (isCancelled(e))
                return;
            this._forgetHandler();
            this._setProfile(null);
        }
    }

    async _write(profile) {
        if (this._handler === null)
            return;

        try {
            // sysfs does not allow the temporary file an atomic replace needs,
            // so GIO falls back to overwriting the attribute in place.
            await Gio.File.new_for_path(`${this._handler}/profile`)
                .replace_contents_bytes_async(
                    new GLib.Bytes(new TextEncoder().encode(profile)),
                    null, false, Gio.FileCreateFlags.NONE, this._cancellable);
        } catch (e) {
            if (isCancelled(e))
                return;
            this._onError(`Cannot change the performance profile: ${e.message}`);
        }
        await this.refresh();
    }

    async enterQuiet() {
        if (this.quiet)
            return;

        try {
            this._previous = await this._daemon.getActive(this._cancellable);
        } catch (e) {
            if (isCancelled(e))
                return;
            this._previous = 'balanced';
        }
        await this._write(QUIET);
    }

    /**
     * Leave quiet for a desktop power mode by writing its firmware profile.
     *
     * The daemon needs about two seconds to notice that quiet was set behind
     * its back, and it never rewrites the firmware profile for the mode it
     * already considers active. Writing the profile here works in both cases.
     */
    async leaveQuietFor(mode) {
        if (!this.quiet)
            return;

        if (mode === 'performance' || mode === 'balanced')
            await this._write(mode);
        else
            await this._write(this._choices.includes('low-power') ? 'low-power' : 'balanced');
    }

    /** Leave quiet for the desktop power mode that was active before it. */
    async leaveQuiet() {
        if (!this.quiet)
            return;

        const mode = this._previous;
        await this.leaveQuietFor(mode);
        if (mode === 'power-saver')
            return;

        // The daemon follows the firmware profile by itself; asking it directly
        // only makes it switch the CPU side without the delay.
        try {
            await this._daemon.setActive(mode, this._cancellable);
        } catch {
            // No daemon: the firmware profile is already set.
        }
    }

    destroy() {
        this._cancellable.cancel();
        this._forgetHandler();
        this._listeners.clear();
    }
}
