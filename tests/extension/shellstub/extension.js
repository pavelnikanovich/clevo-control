// SPDX-License-Identifier: GPL-2.0-or-later
// Stand-in for resource:///org/gnome/shell/extensions/extension.js.

export class Extension {
    constructor() {
        this.uuid = 'clevo-control@test';
    }
}

/** Replaces methods of a prototype and puts the originals back on clear(). */
export class InjectionManager {
    constructor() {
        this._saved = [];
    }

    overrideMethod(prototype, name, createOverride) {
        const original = prototype[name];
        this._saved.push([prototype, name, original]);
        prototype[name] = createOverride(original);
    }

    clear() {
        for (const [prototype, name, original] of this._saved.reverse())
            prototype[name] = original;
        this._saved = [];
    }
}
