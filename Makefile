# SPDX-License-Identifier: GPL-2.0-or-later
# clevo-control: kernel module, tools, GNOME Shell extension.
#
#   make            generate the files that carry the version (man pages, metadata)
#   make module     build the kernel module for the running kernel (no install)
#   make test       run the test suites
#   make lint       run every static check
#   make check      module + test + lint
#   make install    install everything below $(DESTDIR)$(PREFIX); the module is
#                   installed as DKMS source, see README.md
#   make uninstall
#   make deb        build the Debian packages into the parent directory
#   make clean

VERSION  := $(shell cat VERSION)
KVERSION ?= $(shell uname -r)
KDIR     ?= /lib/modules/$(KVERSION)/build

PREFIX      ?= /usr
DESTDIR     ?=
bindir       = $(PREFIX)/bin
datadir      = $(PREFIX)/share
pkgdatadir   = $(datadir)/clevo-control
mandir       = $(datadir)/man
udevrulesdir = $(PREFIX)/lib/udev/rules.d
unitdir      = $(PREFIX)/lib/systemd/system
tmpfilesdir  = $(PREFIX)/lib/tmpfiles.d
dkmsdir      = $(PREFIX)/src/clevo-control-$(VERSION)
sysconfdir  ?= /etc

APP_ID   := io.github.pavelnikanovich.ClevoControl
EXT_UUID := clevo-control@pavelnikanovich.github.io
extdir    = $(datadir)/gnome-shell/extensions/$(EXT_UUID)

BUILD     := build
MAN_PAGES := clevoctl.1 clevo-control-tray.1 clevo-control.7
GENERATED := $(addprefix $(BUILD)/man/,$(MAN_PAGES)) \
             $(BUILD)/extension/metadata.json \
             $(BUILD)/_version \
             $(BUILD)/dkms.conf

all: generate

generate: $(GENERATED)

$(BUILD)/man/%: man/%.in VERSION
	@mkdir -p $(@D)
	sed 's/@VERSION@/$(VERSION)/g' $< > $@

$(BUILD)/extension/metadata.json: extension/metadata.json.in VERSION
	@mkdir -p $(@D)
	sed 's/@VERSION@/$(VERSION)/g' $< > $@

$(BUILD)/_version: VERSION
	@mkdir -p $(@D)
	cp $< $@

$(BUILD)/dkms.conf: module/dkms.conf VERSION
	@mkdir -p $(@D)
	sed 's/#MODULE_VERSION#/$(VERSION)/' $< > $@

module:
	$(MAKE) -C $(KDIR) M=$(CURDIR)/module modules

test:
	python3 -m unittest discover -s tests -t .
	@if command -v gjs >/dev/null; then \
		gjs -m tests/extension/test_controller.js; \
	else \
		echo "gjs not found: extension tests skipped"; \
	fi

lint: generate
	KDIR=$(KDIR) BUILD=$(BUILD) tools/lint.sh

check: module test lint

install: install-tools install-extension install-dkms

install-tools: generate
	install -D -m 755 bin/clevoctl $(DESTDIR)$(bindir)/clevoctl
	install -D -m 755 bin/clevo-control-tray $(DESTDIR)$(bindir)/clevo-control-tray
	install -d $(DESTDIR)$(pkgdatadir)/clevo_control
	install -m 644 clevo_control/*.py $(DESTDIR)$(pkgdatadir)/clevo_control/
	install -m 644 $(BUILD)/_version $(DESTDIR)$(pkgdatadir)/clevo_control/_version
	install -D -m 644 data/70-clevo-control.rules $(DESTDIR)$(udevrulesdir)/70-clevo-control.rules
	install -D -m 644 data/clevo-control-backlight.service $(DESTDIR)$(unitdir)/clevo-control-backlight.service
	install -D -m 644 data/clevo-control.tmpfiles $(DESTDIR)$(tmpfilesdir)/clevo-control.conf
	install -D -m 644 data/$(APP_ID).desktop $(DESTDIR)$(datadir)/applications/$(APP_ID).desktop
	install -D -m 644 data/$(APP_ID)-autostart.desktop $(DESTDIR)$(sysconfdir)/xdg/autostart/$(APP_ID).desktop
	install -D -m 644 data/$(APP_ID).metainfo.xml $(DESTDIR)$(datadir)/metainfo/$(APP_ID).metainfo.xml
	install -D -m 644 $(BUILD)/man/clevoctl.1 $(DESTDIR)$(mandir)/man1/clevoctl.1
	install -D -m 644 $(BUILD)/man/clevo-control-tray.1 $(DESTDIR)$(mandir)/man1/clevo-control-tray.1
	install -D -m 644 $(BUILD)/man/clevo-control.7 $(DESTDIR)$(mandir)/man7/clevo-control.7

install-extension: generate
	install -D -m 644 extension/extension.js $(DESTDIR)$(extdir)/extension.js
	install -D -m 644 extension/controller.js $(DESTDIR)$(extdir)/controller.js
	install -D -m 644 $(BUILD)/extension/metadata.json $(DESTDIR)$(extdir)/metadata.json

install-dkms: generate
	install -D -m 644 module/clevo-control.c $(DESTDIR)$(dkmsdir)/clevo-control.c
	install -D -m 644 module/Kbuild $(DESTDIR)$(dkmsdir)/Kbuild
	install -D -m 644 $(BUILD)/dkms.conf $(DESTDIR)$(dkmsdir)/dkms.conf

uninstall:
	rm -f $(DESTDIR)$(bindir)/clevoctl $(DESTDIR)$(bindir)/clevo-control-tray
	rm -rf $(DESTDIR)$(pkgdatadir) $(DESTDIR)$(extdir) $(DESTDIR)$(dkmsdir)
	rm -f $(DESTDIR)$(udevrulesdir)/70-clevo-control.rules
	rm -f $(DESTDIR)$(unitdir)/clevo-control-backlight.service
	rm -f $(DESTDIR)$(tmpfilesdir)/clevo-control.conf
	rm -f $(DESTDIR)$(datadir)/applications/$(APP_ID).desktop
	rm -f $(DESTDIR)$(sysconfdir)/xdg/autostart/$(APP_ID).desktop
	rm -f $(DESTDIR)$(datadir)/metainfo/$(APP_ID).metainfo.xml
	rm -f $(DESTDIR)$(mandir)/man1/clevoctl.1 $(DESTDIR)$(mandir)/man1/clevo-control-tray.1
	rm -f $(DESTDIR)$(mandir)/man7/clevo-control.7

deb:
	dpkg-buildpackage -us -uc -b

# Does not need kernel headers, so that it works on a build machine without them.
clean:
	rm -rf $(BUILD)
	rm -f module/*.o module/*.ko module/*.mod module/*.mod.c module/.*.cmd \
	      module/Module.symvers module/modules.order
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -rf debian/.debhelper debian/tmp debian/files debian/debhelper-build-stamp \
	       debian/*.substvars debian/*.debhelper debian/*.debhelper.log \
	       debian/clevo-control debian/clevo-control-dkms \
	       debian/gnome-shell-extension-clevo-control

# The install targets create the same parent directories; run in parallel
# (debhelper passes -j) they race, and there is nothing here worth parallelising.
.NOTPARALLEL:

.PHONY: all generate module test lint check install install-tools install-extension \
        install-dkms uninstall deb clean
