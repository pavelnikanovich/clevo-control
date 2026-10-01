// SPDX-License-Identifier: GPL-2.0-or-later
// Stand-in for resource:///org/gnome/shell/ui/popupMenu.js.

export const Ornament = {NONE: 0, DOT: 1, CHECK: 2, HIDDEN: 3};

export class PopupImageMenuItem {
    constructor(text, _icon) {
        this.text = text;
        // As in the shell: a new item shows no ornament until it is given one.
        this.ornament = Ornament.HIDDEN;
        this.handlers = new Map();
        this._nextId = 1;
        this._section = null;
    }

    connect(signal, callback) {
        this.handlers.set(this._nextId, [signal, callback]);
        return this._nextId++;
    }

    disconnect(id) {
        if (!this.handlers.delete(id))
            throw new Error(`disconnect of unknown handler ${id}`);
    }

    activate() {
        for (const [signal, callback] of [...this.handlers.values()]) {
            if (signal === 'activate')
                callback(this);
        }
    }

    setOrnament(ornament) {
        this.ornament = ornament;
    }

    destroy() {
        this.handlers.clear();
        if (this._section)
            this._section.items = this._section.items.filter(item => item !== this);
    }
}

export class PopupMenuSection {
    constructor() {
        this.items = [];
    }

    addMenuItem(item) {
        item._section = this;
        this.items.push(item);
    }

    removeAll() {
        for (const item of [...this.items])
            item.destroy();
    }
}
