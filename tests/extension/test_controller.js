// SPDX-License-Identifier: GPL-2.0-or-later
//
// Tests of extension/controller.js against a fake platform-profile class
// directory. Run: gjs -m tests/extension/test_controller.js

import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import System from 'system';

import {ProfileController} from '../../extension/controller.js';

const loop = new GLib.MainLoop(null, false);
let failures = 0;

function check(name, got, want) {
    const ok = JSON.stringify(got) === JSON.stringify(want);
    if (!ok)
        failures++;
    print(`${ok ? 'ok  ' : 'FAIL'} ${name}${ok ? '' : `: got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`}`);
}

function write(path, text) {
    GLib.file_set_contents(path, text);
}

function read(path) {
    const [, bytes] = GLib.file_get_contents(path);
    return new TextDecoder().decode(bytes).trim();
}

function addHandler(classDir, entry, name, profile) {
    const dir = `${classDir}/${entry}`;
    GLib.mkdir_with_parents(dir, 0o755);
    write(`${dir}/name`, `${name}\n`);
    write(`${dir}/choices`, 'low-power quiet balanced performance\n');
    write(`${dir}/profile`, `${profile}\n`);
    return dir;
}

function removeDir(dir) {
    for (const name of ['name', 'choices', 'profile'])
        GLib.unlink(`${dir}/${name}`);
    GLib.rmdir(dir);
}

function sleep(ms) {
    return new Promise(resolve => GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => {
        resolve();
        return GLib.SOURCE_REMOVE;
    }));
}

/** Stand-in for power-profiles-daemon. */
class FakeDaemon {
    constructor(active) {
        this.active = active;
        this.calls = [];
        this.fail = false;
    }

    async getActive() {
        if (this.fail)
            throw new Error('no daemon');
        return this.active;
    }

    async setActive(mode) {
        if (this.fail)
            throw new Error('no daemon');
        this.calls.push(mode);
        this.active = mode;
    }
}

async function main() {
    const root = GLib.Dir.make_tmp('clevo-control-test-XXXXXX');
    const classDir = `${root}/platform-profile`;
    const errors = [];
    const daemon = new FakeDaemon('balanced');
    let changes = 0;

    const controller = new ProfileController({
        daemon, classDir, onError: message => errors.push(message),
    });
    controller.watch(() => changes++);

    await controller.refresh();
    check('no class directory: not available', controller.available, false);

    addHandler(classDir, 'platform-profile-0', 'other', 'performance');
    const dir = addHandler(classDir, 'platform-profile-1', 'clevo', 'balanced');
    await controller.refresh();
    check('finds the clevo handler under any index', controller.profile, 'balanced');
    check('listener called on change', changes, 1);

    await controller.enterQuiet();
    check('enterQuiet writes quiet', read(`${dir}/profile`), 'quiet');
    check('quiet', controller.quiet, true);

    await controller.leaveQuiet();
    check('leaveQuiet writes the previous mode', read(`${dir}/profile`), 'balanced');
    check('leaveQuiet asks the daemon for the previous mode', daemon.calls, ['balanced']);

    daemon.active = 'power-saver';
    daemon.calls = [];
    await controller.enterQuiet();
    await controller.leaveQuiet();
    check('previous power-saver: firmware gets low-power', read(`${dir}/profile`), 'low-power');
    check('previous power-saver: daemon is not asked', daemon.calls, []);

    await controller.enterQuiet();
    await controller.leaveQuietFor('performance');
    check('leaveQuietFor writes the chosen mode', read(`${dir}/profile`), 'performance');
    await controller.leaveQuietFor('balanced');
    check('leaveQuietFor does nothing when not quiet', read(`${dir}/profile`), 'performance');

    daemon.fail = true;
    await controller.enterQuiet();
    check('enterQuiet without a daemon', read(`${dir}/profile`), 'quiet');
    await controller.leaveQuiet();
    check('leaveQuiet without a daemon falls back to balanced', read(`${dir}/profile`), 'balanced');
    daemon.fail = false;

    write(`${dir}/profile`, 'performance\n');
    await sleep(1500);
    check('external change is noticed through the file monitor', controller.profile, 'performance');

    // Module reload: the handler disappears and comes back under another index.
    removeDir(dir);
    await controller.refresh();
    check('handler removed: not available', controller.available, false);
    const dir2 = addHandler(classDir, 'platform-profile-7', 'clevo', 'low-power');
    await controller.refresh();
    check('handler re-created: found again', controller.profile, 'low-power');
    await controller.enterQuiet();
    check('writes go to the new handler', read(`${dir2}/profile`), 'quiet');
    write(`${dir2}/profile`, 'balanced\n');
    await sleep(1500);
    check('monitor follows the new handler', controller.profile, 'balanced');

    // A profile attribute that cannot be written reports an error and changes nothing.
    // Permission checks do not apply to root (USER may be unset, as in a container).
    if (new Gio.Credentials().get_unix_user() !== 0) {
        GLib.chmod(`${dir2}/profile`, 0o444);
        GLib.chmod(dir2, 0o555);
        await controller.enterQuiet();
        check('unwritable profile: error reported', errors.length, 1);
        check('unwritable profile: state unchanged', controller.profile, 'balanced');
        GLib.chmod(dir2, 0o755);
        GLib.chmod(`${dir2}/profile`, 0o644);
    }

    const before = changes;
    controller.destroy();
    write(`${dir2}/profile`, 'performance\n');
    await sleep(1200);
    check('no callbacks after destroy', changes, before);
    await controller.refresh();
    check('refresh after destroy does nothing', controller.profile, 'balanced');

    removeDir(dir2);
    removeDir(`${classDir}/platform-profile-0`);
    GLib.rmdir(classDir);
    GLib.rmdir(root);
}

main().catch(e => {
    failures++;
    printerr(`test run failed: ${e}\n${e.stack ?? ''}`);
}).finally(() => loop.quit());
loop.run();
System.exit(failures ? 1 : 0);
