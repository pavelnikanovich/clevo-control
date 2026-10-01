// SPDX-License-Identifier: GPL-2.0-or-later
//
// Tests of extension/extension.js against stand-ins for the GNOME Shell modules
// it imports (tests/extension/shellstub). Run through run-extension-test.sh,
// which puts a copy of the extension with rewritten imports next to this file
// and points it at a fake platform-profile directory (argument 1).

import GLib from 'gi://GLib';
import System from 'system';

import Extension from './extension.js';
import * as Main from './shellstub/main.js';
import {Ornament} from './shellstub/popupMenu.js';

const classDir = ARGV[0];
const profileFile = `${classDir}/platform-profile-0/profile`;
const toggle = Main.toggle;
const loop = new GLib.MainLoop(null, false);
let failures = 0;

function check(name, got, want) {
    const ok = JSON.stringify(got) === JSON.stringify(want);
    if (!ok)
        failures++;
    print(`${ok ? 'ok  ' : 'FAIL'} ${name}${ok ? '' : `: got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`}`);
}

function sleep(ms) {
    return new Promise(resolve => GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => {
        resolve();
        return GLib.SOURCE_REMOVE;
    }));
}

function firmwareProfile() {
    const [, bytes] = GLib.file_get_contents(profileFile);
    return new TextDecoder().decode(bytes).trim();
}

/** The menu as the user sees it: entries, with the checked one marked. */
function menu() {
    return toggle._profileSection.items
        .map(item => item.ornament === Ornament.CHECK ? `[${item.text}]` : item.text);
}

function item(text) {
    return toggle._profileSection.items.find(i => i.text === text);
}

function shellHandlerCounts() {
    return {
        items: [...toggle._profileItems.values()].map(i => i.handlers.size),
        toggle: toggle.handlers.size,
        proxy: toggle._proxy.handlers.size,
        menu: Main.quickSettingsMenu.handlers.size,
    };
}

async function main() {
    const prototype = Object.getPrototypeOf(toggle);
    const original = {sync: prototype._sync, syncProfiles: prototype._syncProfiles};
    const stock = shellHandlerCounts();
    check('stock menu', menu(), ['Performance', '[Balanced]', 'Power Saver']);

    const extension = new Extension();
    extension.enable();
    await sleep(300);
    check('Quiet is added and the active mode keeps its check mark',
        menu(), ['Performance', '[Balanced]', 'Power Saver', 'Quiet']);
    check('no separate toggle while the menu is used', Main.externalIndicators.length, 0);

    item('Quiet').activate();
    await sleep(300);
    check('choosing Quiet sets the firmware profile', firmwareProfile(), 'quiet');
    check('only Quiet is checked', menu(), ['Performance', 'Balanced', 'Power Saver', '[Quiet]']);
    check('subtitle says Quiet', toggle.subtitle, 'Quiet');

    item('Performance').activate();
    await sleep(300);
    check('choosing another mode leaves quiet at once', firmwareProfile(), 'performance');
    toggle._sync();
    check('the chosen mode is checked', menu(), ['[Performance]', 'Balanced', 'Power Saver', 'Quiet']);

    item('Quiet').activate();
    await sleep(300);
    item('Power Saver').activate();
    await sleep(300);
    check('Power Saver from quiet selects low-power', firmwareProfile(), 'low-power');

    // The shell rebuilds its menu when the daemon's profile list changes.
    toggle._syncProfiles();
    toggle._sync();
    check('Quiet survives a rebuild of the menu, once', menu().filter(t => t.includes('Quiet')).length, 1);

    // power-profiles-daemon stops: the shell hides its toggle.
    toggle.setDaemonOwner(null);
    await sleep(100);
    check('without the daemon a separate toggle is shown', Main.externalIndicators.length, 1);
    check('and the menu entry is gone', menu().some(t => t.includes('Quiet')), false);
    const fallback = Main.externalIndicators[0].quickSettingsItems[0];
    fallback.emit('clicked');
    await sleep(300);
    check('the separate toggle enters quiet', firmwareProfile(), 'quiet');
    check('and shows it', fallback.checked, true);

    toggle.setDaemonOwner(':1.2');
    await sleep(100);
    check('daemon back: the separate toggle is destroyed', fallback.destroyed, true);
    check('and Quiet is in the menu again, once',
        menu().filter(t => t.includes('Quiet')).length, 1);

    extension.disable();
    await sleep(100);
    check('after disable the menu is the stock one', menu().some(t => t.includes('Quiet')), false);
    check('prototype methods are restored',
        [prototype._sync === original.sync, prototype._syncProfiles === original.syncProfiles],
        [true, true]);
    check('no handler of the extension is left on shell objects', shellHandlerCounts(), stock);

    // Enabled again while the daemon is absent, then disabled: nothing left either.
    toggle.setDaemonOwner(null);
    extension.enable();
    await sleep(300);
    check('enabled without the daemon: separate toggle', Main.externalIndicators.length, 2);
    extension.disable();
    toggle.setDaemonOwner(':1.3');
    await sleep(100);
    check('and nothing is left after disable', shellHandlerCounts(), stock);
    check('no errors were reported', Main.errors, []);
}

main().catch(e => {
    failures++;
    printerr(`test run failed: ${e}\n${e.stack ?? ''}`);
}).finally(() => loop.quit());
loop.run();
System.exit(failures ? 1 : 0);
