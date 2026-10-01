// SPDX-License-Identifier: GPL-2.0-or-later
// Stand-in for resource:///org/gnome/shell/ui/quickSettings.js.

import GObject from 'gi://GObject';

export const QuickToggle = GObject.registerClass({
    Properties: {
        'title': GObject.ParamSpec.string('title', '', '', GObject.ParamFlags.READWRITE, ''),
        'icon-name': GObject.ParamSpec.string('icon-name', '', '', GObject.ParamFlags.READWRITE, ''),
        'toggle-mode': GObject.ParamSpec.boolean('toggle-mode', '', '', GObject.ParamFlags.READWRITE, false),
        'visible': GObject.ParamSpec.boolean('visible', '', '', GObject.ParamFlags.READWRITE, true),
        'checked': GObject.ParamSpec.boolean('checked', '', '', GObject.ParamFlags.READWRITE, false),
    },
    Signals: {'destroy': {}, 'clicked': {}},
}, class QuickToggle extends GObject.Object {
    destroy() {
        this.emit('destroy');
        this.destroyed = true;
    }
});

export const SystemIndicator = GObject.registerClass(
class SystemIndicator extends GObject.Object {
    _init() {
        super._init();
        this.quickSettingsItems = [];
    }

    destroy() {
        this.destroyed = true;
    }
});
