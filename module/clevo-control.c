// SPDX-License-Identifier: GPL-2.0-or-later
/*
 * clevo-control: keyboard backlight, hotkeys and performance profiles of
 * Clevo laptops.
 *
 * The firmware is reached through the ACPI device CLV0001 on models that have
 * it and through the Clevo WMI interface on older ones. Everything is exposed
 * through standard kernel interfaces:
 *
 *  - the RGB keyboard backlight as the multicolor LED "rgb:kbd_backlight";
 *  - the backlight hotkeys as input key events (the "next color" key is
 *    handled here);
 *  - the firmware performance profiles as a platform profile.
 *
 * The firmware protocol (command and sub-command numbers, keyboard type
 * detection, hotkey event codes, 1-zone color calibration factors and the
 * performance profile numbering) is taken from tuxedo-drivers v4.24.0:
 * https://gitlab.com/tuxedocomputers/development/packages/tuxedo-drivers
 *
 * Copyright (c) 2026 Pavel Nikanovich <pavelnikanovich@gmail.com>
 * Firmware protocol: Copyright (c) TUXEDO Computers GmbH <tux@tuxedocomputers.com>
 */

#include <linux/acpi.h>
#include <linux/cleanup.h>
#include <linux/delay.h>
#include <linux/device.h>
#include <linux/dmi.h>
#include <linux/input.h>
#include <linux/input/sparse-keymap.h>
#include <linux/led-class-multicolor.h>
#include <linux/leds.h>
#include <linux/minmax.h>
#include <linux/mod_devicetable.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/platform_device.h>
#include <linux/platform_profile.h>
#include <linux/pm.h>
#include <linux/slab.h>
#include <linux/types.h>
#include <linux/uuid.h>
#include <linux/wmi.h>

#define CLEVO_ACPI_HID			"CLV0001"
#define CLEVO_WMI_EVENT_GUID		"ABBC0F6B-8EA1-11D1-00A0-C90629100000"
#define CLEVO_WMI_METHOD_GUID		"ABBC0F6D-8EA1-11D1-00A0-C90629100000"

/* 93f224e4-fbdc-4bbf-add6-db71bdc0afad */
static const guid_t clevo_dsm_guid =
	GUID_INIT(0x93f224e4, 0xfbdc, 0x4bbf,
		  0xad, 0xd6, 0xdb, 0x71, 0xbd, 0xc0, 0xaf, 0xad);

/* Firmware commands. The argument is one 32 bit integer. */
#define CLEVO_CMD_GET_EVENT		0x01
#define CLEVO_CMD_GET_SPECS		0x0d	/* returns a buffer */
#define CLEVO_CMD_SET_EVENTS_ENABLED	0x46
#define CLEVO_CMD_GET_BIOS_FEATURES_1	0x52
#define CLEVO_CMD_SET_KB_RGB_LEDS	0x67
#define CLEVO_CMD_OPT			0x79

/* Sub-commands of CLEVO_CMD_SET_KB_RGB_LEDS, selected by the top byte. */
#define CLEVO_KB_SUB_RGB_ZONE(n)	(0xf0000000 | ((u32)(n) << 24))
#define CLEVO_KB_SUB_RGB_BRIGHTNESS	0xf4000000

/* Sub-command of CLEVO_CMD_OPT: performance profile in the low byte. */
#define CLEVO_OPT_SUB_PERF_PROFILE	0x19000000
#define CLEVO_PERF_PROFILE_QUIET	0x00
#define CLEVO_PERF_PROFILE_POWER_SAVING	0x01
#define CLEVO_PERF_PROFILE_PERFORMANCE	0x02
#define CLEVO_PERF_PROFILE_ENTERTAINMENT 0x03

#define CLEVO_FEATURES_1_INVALID	0xffffffff
#define CLEVO_FEATURES_1_3_ZONE_RGB_KB	0x00400000

#define CLEVO_SPECS_LEN			0x10
#define CLEVO_SPECS_ATTEMPTS		3
#define CLEVO_SPECS_KB_TYPE		0x0f
#define CLEVO_KB_TYPE_3_ZONE_RGB	0x02
#define CLEVO_KB_TYPE_1_ZONE_RGB	0x06

#define CLEVO_KB_BRIGHTNESS_MAX		0xff
#define CLEVO_KB_BRIGHTNESS_DEFAULT	0x80

/* Hotkey event codes */
#define CLEVO_EVENT_KB_DECREASE		0x81
#define CLEVO_EVENT_KB_INCREASE		0x82
#define CLEVO_EVENT_KB_NEXT_COLOR	0x83
#define CLEVO_EVENT_KB_TOGGLE		0x9f
#define CLEVO_EVENT_KB_DECREASE_ALT	0x20
#define CLEVO_EVENT_KB_INCREASE_ALT	0x21
#define CLEVO_EVENT_KB_TOGGLE_ALT	0x3f
#define CLEVO_EVENT_TOUCHPAD_TOGGLE	0x5d
#define CLEVO_EVENT_TOUCHPAD_OFF	0xfc
#define CLEVO_EVENT_TOUCHPAD_ON		0xfd
#define CLEVO_EVENT_RFKILL		0x85
#define CLEVO_EVENT_RFKILL_OLD		0x86
#define CLEVO_EVENT_VOLUME		0xfa
#define CLEVO_EVENT_MUTE		0xfb

static bool force_rgb;
module_param(force_rgb, bool, 0444);
MODULE_PARM_DESC(force_rgb,
		 "Treat the keyboard as 1-zone RGB when the firmware reports no RGB keyboard");

static bool force_profiles;
module_param(force_profiles, bool, 0444);
MODULE_PARM_DESC(force_profiles,
		 "Register the performance profiles on a board they were not verified on");

struct clevo_laptop;

/**
 * struct clevo_transport - how firmware commands reach the firmware
 * @call: evaluate a command; store the integer reply in @result if not NULL
 * @read: evaluate a command that replies with a buffer; copy up to @len bytes
 *	  and return the number of bytes copied
 */
struct clevo_transport {
	int (*call)(struct device *dev, u32 cmd, u32 arg, u32 *result);
	int (*read)(struct device *dev, u32 cmd, u32 arg, u8 *buf, size_t len);
};

struct clevo_laptop {
	struct device *dev;
	const struct clevo_transport *transport;
	/* Serializes multi-command sequences and protects @profile. */
	struct mutex lock;

	/* RGB keyboard; @zones is 0 if there is none */
	unsigned int zones;
	struct led_classdev_mc mc;
	struct mc_subled subleds[3];
	struct input_dev *input;

	bool has_profiles;
	enum platform_profile_option profile;
};

static int clevo_fw_call(struct clevo_laptop *laptop, u32 cmd, u32 arg, u32 *result)
{
	return laptop->transport->call(laptop->dev, cmd, arg, result);
}

/* Copy an integer or buffer reply out of an ACPI object. */
static int clevo_reply_integer(const union acpi_object *obj, u32 *result)
{
	if (!result)
		return 0;
	if (!obj || obj->type != ACPI_TYPE_INTEGER)
		return -EIO;

	*result = (u32)obj->integer.value;
	return 0;
}

static int clevo_reply_buffer(const union acpi_object *obj, u8 *buf, size_t len)
{
	if (!obj || obj->type != ACPI_TYPE_BUFFER)
		return -EIO;

	len = min_t(size_t, len, obj->buffer.length);
	memcpy(buf, obj->buffer.pointer, len);
	return len;
}

/*
 * Keyboard backlight
 */

/* The firmware expects the color packed as blue, red, green. */
static u32 clevo_kb_pack_color(u8 red, u8 green, u8 blue)
{
	return ((u32)blue << 16) | ((u32)red << 8) | green;
}

/* Must be called with laptop->lock held. */
static int clevo_kb_apply(struct clevo_laptop *laptop, unsigned int brightness)
{
	u8 red = min(laptop->subleds[0].intensity, 0xffU);
	u8 green = min(laptop->subleds[1].intensity, 0xffU);
	u8 blue = min(laptop->subleds[2].intensity, 0xffU);
	unsigned int zone;
	int ret;

	/* Without this, white looks blueish-pink on 1-zone keyboards. */
	if (laptop->zones == 1) {
		red = (180 * red) / 255;
		blue = (200 * blue) / 255;
	}

	for (zone = 0; zone < laptop->zones; zone++) {
		ret = clevo_fw_call(laptop, CLEVO_CMD_SET_KB_RGB_LEDS,
				    CLEVO_KB_SUB_RGB_ZONE(zone) |
				    clevo_kb_pack_color(red, green, blue), NULL);
		if (ret)
			return ret;
	}

	return clevo_fw_call(laptop, CLEVO_CMD_SET_KB_RGB_LEDS,
			     CLEVO_KB_SUB_RGB_BRIGHTNESS |
			     min(brightness, CLEVO_KB_BRIGHTNESS_MAX), NULL);
}

static int clevo_led_set(struct led_classdev *led_cdev, enum led_brightness brightness)
{
	struct led_classdev_mc *mc = lcdev_to_mccdev(led_cdev);
	struct clevo_laptop *laptop = container_of(mc, struct clevo_laptop, mc);

	guard(mutex)(&laptop->lock);
	return clevo_kb_apply(laptop, brightness);
}

/* Colors stepped through by the "next color" hotkey, as 0xRRGGBB. */
static const u32 clevo_kb_palette[] = {
	0xffffff, 0xff0000, 0xff8000, 0xffff00, 0x00ff00,
	0x00ffff, 0x0000ff, 0x8000ff, 0xff4080,
};

/*
 * Change the color the way a write to multi_intensity does, so that the LED
 * core keeps the keyboard dark while suspended and reports the new color.
 */
static void clevo_led_next_color(struct clevo_laptop *laptop)
{
	struct led_classdev *led_cdev = &laptop->mc.led_cdev;
	unsigned int i, next = 0;
	u32 color;

	guard(mutex)(&led_cdev->led_access);

	color = (laptop->subleds[0].intensity << 16) |
		(laptop->subleds[1].intensity << 8) |
		laptop->subleds[2].intensity;
	for (i = 0; i < ARRAY_SIZE(clevo_kb_palette); i++) {
		if (clevo_kb_palette[i] == color) {
			next = (i + 1) % ARRAY_SIZE(clevo_kb_palette);
			break;
		}
	}

	laptop->subleds[0].intensity = (clevo_kb_palette[next] >> 16) & 0xff;
	laptop->subleds[1].intensity = (clevo_kb_palette[next] >> 8) & 0xff;
	laptop->subleds[2].intensity = clevo_kb_palette[next] & 0xff;
	/* A software blink picks the new color up at its next step. */
	if (!test_bit(LED_BLINK_SW, &led_cdev->work_flags))
		led_set_brightness(led_cdev, led_cdev->brightness);
}

static int clevo_led_register(struct clevo_laptop *laptop)
{
	struct led_classdev *led_cdev = &laptop->mc.led_cdev;
	int ret;

	laptop->subleds[0].color_index = LED_COLOR_ID_RED;
	laptop->subleds[1].color_index = LED_COLOR_ID_GREEN;
	laptop->subleds[2].color_index = LED_COLOR_ID_BLUE;
	laptop->subleds[0].intensity = 0xff;
	laptop->subleds[1].intensity = 0xff;
	laptop->subleds[2].intensity = 0xff;

	laptop->mc.subled_info = laptop->subleds;
	laptop->mc.num_colors = ARRAY_SIZE(laptop->subleds);
	led_cdev->name = "rgb:" LED_FUNCTION_KBD_BACKLIGHT;
	led_cdev->max_brightness = CLEVO_KB_BRIGHTNESS_MAX;
	led_cdev->brightness = CLEVO_KB_BRIGHTNESS_DEFAULT;
	led_cdev->brightness_set_blocking = clevo_led_set;
	led_cdev->flags = LED_CORE_SUSPENDRESUME;

	/*
	 * The firmware cannot be asked for the current color and brightness,
	 * so start from a known state. User space restores its own afterwards.
	 */
	scoped_guard(mutex, &laptop->lock)
		ret = clevo_kb_apply(laptop, led_cdev->brightness);
	if (ret)
		return ret;

	return devm_led_classdev_multicolor_register(laptop->dev, &laptop->mc);
}

/*
 * Hotkeys
 */

static const struct key_entry clevo_keymap[] = {
	{ KE_KEY, CLEVO_EVENT_KB_DECREASE, { KEY_KBDILLUMDOWN } },
	{ KE_KEY, CLEVO_EVENT_KB_INCREASE, { KEY_KBDILLUMUP } },
	{ KE_KEY, CLEVO_EVENT_KB_TOGGLE, { KEY_KBDILLUMTOGGLE } },
	{ KE_KEY, CLEVO_EVENT_KB_DECREASE_ALT, { KEY_KBDILLUMDOWN } },
	{ KE_KEY, CLEVO_EVENT_KB_INCREASE_ALT, { KEY_KBDILLUMUP } },
	{ KE_KEY, CLEVO_EVENT_KB_TOGGLE_ALT, { KEY_KBDILLUMTOGGLE } },
	/* KEY_F21 is what desktops treat as the touchpad toggle key. */
	{ KE_KEY, CLEVO_EVENT_TOUCHPAD_TOGGLE, { KEY_F21 } },
	{ KE_KEY, CLEVO_EVENT_TOUCHPAD_OFF, { KEY_F21 } },
	{ KE_KEY, CLEVO_EVENT_TOUCHPAD_ON, { KEY_F21 } },
	{ KE_KEY, CLEVO_EVENT_RFKILL, { KEY_RFKILL } },
	{ KE_IGNORE, CLEVO_EVENT_RFKILL_OLD },
	/* The firmware changes the volume itself. */
	{ KE_IGNORE, CLEVO_EVENT_VOLUME },
	{ KE_IGNORE, CLEVO_EVENT_MUTE },
	{ KE_END }
};

static int clevo_input_register(struct clevo_laptop *laptop)
{
	struct input_dev *input;
	int ret;

	input = devm_input_allocate_device(laptop->dev);
	if (!input)
		return -ENOMEM;

	input->name = "Clevo hotkeys";
	input->phys = KBUILD_MODNAME "/input0";
	input->id.bustype = BUS_HOST;

	ret = sparse_keymap_setup(input, clevo_keymap, NULL);
	if (ret)
		return ret;

	ret = input_register_device(input);
	if (ret)
		return ret;

	laptop->input = input;
	return 0;
}

/* Called by the back-ends for every firmware event, in process context. */
static void clevo_laptop_event(struct clevo_laptop *laptop, u32 event)
{
	if (event == CLEVO_EVENT_KB_NEXT_COLOR) {
		clevo_led_next_color(laptop);
		return;
	}

	if (!sparse_keymap_report_event(laptop->input, event, 1, true))
		dev_dbg(laptop->dev, "unhandled event 0x%02x\n", event);
}

/* Ask the firmware to report hotkeys instead of acting on them itself. */
static void clevo_laptop_enable_events(struct clevo_laptop *laptop)
{
	if (laptop->input)
		clevo_fw_call(laptop, CLEVO_CMD_SET_EVENTS_ENABLED, 0, NULL);
}

/*
 * Performance profiles
 */

/* Boards on which the effect of the profile command has been measured. */
static const struct dmi_system_id clevo_profile_boards[] = {
	{
		.matches = {
			DMI_EXACT_MATCH(DMI_BOARD_NAME, "NH5x_NH7xHP"),
		},
	},
	{ }
};

static int clevo_profile_to_fw(enum platform_profile_option profile)
{
	switch (profile) {
	case PLATFORM_PROFILE_QUIET:
		return CLEVO_PERF_PROFILE_QUIET;
	case PLATFORM_PROFILE_LOW_POWER:
		return CLEVO_PERF_PROFILE_POWER_SAVING;
	case PLATFORM_PROFILE_BALANCED:
		return CLEVO_PERF_PROFILE_ENTERTAINMENT;
	case PLATFORM_PROFILE_PERFORMANCE:
		return CLEVO_PERF_PROFILE_PERFORMANCE;
	default:
		return -EOPNOTSUPP;
	}
}

/* Must be called with laptop->lock held. */
static int clevo_profile_apply(struct clevo_laptop *laptop,
			       enum platform_profile_option profile)
{
	int fw_profile, ret;

	fw_profile = clevo_profile_to_fw(profile);
	if (fw_profile < 0)
		return fw_profile;

	ret = clevo_fw_call(laptop, CLEVO_CMD_OPT,
			    CLEVO_OPT_SUB_PERF_PROFILE | fw_profile, NULL);
	if (ret)
		return ret;

	laptop->profile = profile;
	return 0;
}

static int clevo_profile_probe(void *drvdata, unsigned long *choices)
{
	__set_bit(PLATFORM_PROFILE_QUIET, choices);
	__set_bit(PLATFORM_PROFILE_LOW_POWER, choices);
	__set_bit(PLATFORM_PROFILE_BALANCED, choices);
	__set_bit(PLATFORM_PROFILE_PERFORMANCE, choices);

	return 0;
}

static int clevo_profile_get(struct device *dev, enum platform_profile_option *profile)
{
	struct clevo_laptop *laptop = dev_get_drvdata(dev);

	guard(mutex)(&laptop->lock);
	*profile = laptop->profile;
	return 0;
}

static int clevo_profile_set(struct device *dev, enum platform_profile_option profile)
{
	struct clevo_laptop *laptop = dev_get_drvdata(dev);

	guard(mutex)(&laptop->lock);
	return clevo_profile_apply(laptop, profile);
}

static const struct platform_profile_ops clevo_profile_ops = {
	.probe = clevo_profile_probe,
	.profile_get = clevo_profile_get,
	.profile_set = clevo_profile_set,
};

static int clevo_profile_register(struct clevo_laptop *laptop)
{
	struct device *ppdev;
	int ret;

	/*
	 * The firmware gives no way to ask whether it implements the profile
	 * command, so it is only offered where its effect has been measured.
	 */
	if (!force_profiles && !dmi_check_system(clevo_profile_boards))
		return 0;

	/*
	 * The active profile cannot be read either. Set one, so that the
	 * profile reported from now on is the real one.
	 */
	scoped_guard(mutex, &laptop->lock)
		ret = clevo_profile_apply(laptop, PLATFORM_PROFILE_BALANCED);
	if (ret)
		return ret;

	ppdev = devm_platform_profile_register(laptop->dev, "clevo", laptop,
					       &clevo_profile_ops);
	if (IS_ERR(ppdev))
		return PTR_ERR(ppdev);

	laptop->has_profiles = true;
	return 0;
}

/*
 * Core
 */

/*
 * Returns the number of RGB keyboard zones, 0 if there is no RGB keyboard, or
 * a negative error if the firmware does not speak this interface.
 */
static int clevo_kb_detect_zones(struct clevo_laptop *laptop)
{
	u8 specs[CLEVO_SPECS_LEN] = { };
	unsigned int attempt;
	u32 features;
	int ret;

	/* Nothing may be written to the firmware before this check. */
	ret = clevo_fw_call(laptop, CLEVO_CMD_GET_BIOS_FEATURES_1, 0, &features);
	if (ret || features == CLEVO_FEATURES_1_INVALID)
		return -ENODEV;

	/*
	 * Older firmware has no GET_SPECS and reports 3-zone RGB as a feature.
	 * Newer firmware sometimes answers GET_SPECS with type 0 at first.
	 */
	for (attempt = 0; attempt < CLEVO_SPECS_ATTEMPTS; attempt++) {
		if (attempt)
			msleep(50);

		ret = laptop->transport->read(laptop->dev, CLEVO_CMD_GET_SPECS, 0,
					      specs, sizeof(specs));
		if (ret <= CLEVO_SPECS_KB_TYPE || specs[CLEVO_SPECS_KB_TYPE])
			break;
	}
	dev_dbg(laptop->dev, "keyboard type 0x%02x, features 0x%08x\n",
		specs[CLEVO_SPECS_KB_TYPE], features);

	if (ret > CLEVO_SPECS_KB_TYPE) {
		switch (specs[CLEVO_SPECS_KB_TYPE]) {
		case CLEVO_KB_TYPE_1_ZONE_RGB:
			return 1;
		case CLEVO_KB_TYPE_3_ZONE_RGB:
			return 3;
		}
	} else if (features & CLEVO_FEATURES_1_3_ZONE_RGB_KB) {
		return 3;
	}

	return force_rgb ? 1 : 0;
}

static struct clevo_laptop *clevo_laptop_probe(struct device *dev,
					       const struct clevo_transport *transport)
{
	struct clevo_laptop *laptop;
	int ret;

	laptop = devm_kzalloc(dev, sizeof(*laptop), GFP_KERNEL);
	if (!laptop)
		return ERR_PTR(-ENOMEM);

	laptop->dev = dev;
	laptop->transport = transport;
	ret = devm_mutex_init(dev, &laptop->lock);
	if (ret)
		return ERR_PTR(ret);

	ret = clevo_kb_detect_zones(laptop);
	if (ret < 0)
		return ERR_PTR(ret);
	laptop->zones = ret;

	dev_set_drvdata(dev, laptop);

	/*
	 * The hotkeys are only taken over from the firmware together with an
	 * RGB keyboard: its brightness keys need the operating system, while
	 * on other keyboards the firmware handles them by itself.
	 */
	if (laptop->zones) {
		ret = clevo_led_register(laptop);
		if (ret)
			return ERR_PTR(dev_err_probe(dev, ret,
						     "failed to set up the keyboard backlight\n"));

		ret = clevo_input_register(laptop);
		if (ret)
			return ERR_PTR(ret);

		dev_info(dev, "%u-zone RGB keyboard backlight\n", laptop->zones);
	}

	ret = clevo_profile_register(laptop);
	if (ret)
		dev_warn(dev, "performance profiles not available: %d\n", ret);
	else if (laptop->has_profiles)
		dev_info(dev, "performance profiles enabled\n");

	if (!laptop->zones && !laptop->has_profiles)
		return ERR_PTR(-ENODEV);

	return laptop;
}

static int clevo_laptop_resume(struct device *dev)
{
	struct clevo_laptop *laptop = dev_get_drvdata(dev);

	/*
	 * The firmware may forget both across suspend. Color and brightness
	 * are restored by the LED core (LED_CORE_SUSPENDRESUME).
	 */
	clevo_laptop_enable_events(laptop);

	if (laptop->has_profiles) {
		guard(mutex)(&laptop->lock);
		clevo_profile_apply(laptop, laptop->profile);
	}

	return 0;
}

static DEFINE_SIMPLE_DEV_PM_OPS(clevo_pm_ops, NULL, clevo_laptop_resume);

/*
 * ACPI back-end: commands through the _DSM of CLV0001, hotkeys as ACPI
 * notifications whose value is the event code.
 */

static union acpi_object *clevo_acpi_evaluate(struct device *dev, u32 cmd, u32 arg)
{
	union acpi_object element = {
		.integer.type = ACPI_TYPE_INTEGER,
		.integer.value = arg,
	};
	union acpi_object argv4 = {
		.package.type = ACPI_TYPE_PACKAGE,
		.package.count = 1,
		.package.elements = &element,
	};

	return acpi_evaluate_dsm(ACPI_HANDLE(dev), &clevo_dsm_guid, 0, cmd, &argv4);
}

static int clevo_acpi_call(struct device *dev, u32 cmd, u32 arg, u32 *result)
{
	union acpi_object *obj;
	int ret;

	obj = clevo_acpi_evaluate(dev, cmd, arg);
	if (!obj)
		return -EIO;

	ret = clevo_reply_integer(obj, result);
	ACPI_FREE(obj);
	return ret;
}

static int clevo_acpi_read(struct device *dev, u32 cmd, u32 arg, u8 *buf, size_t len)
{
	union acpi_object *obj;
	int ret;

	obj = clevo_acpi_evaluate(dev, cmd, arg);
	if (!obj)
		return -EIO;

	ret = clevo_reply_buffer(obj, buf, len);
	ACPI_FREE(obj);
	return ret;
}

static const struct clevo_transport clevo_acpi_transport = {
	.call = clevo_acpi_call,
	.read = clevo_acpi_read,
};

static void clevo_acpi_notify(acpi_handle handle, u32 event, void *data)
{
	struct clevo_laptop *laptop = data;

	/* The firmware expects the pending event to be fetched. */
	clevo_fw_call(laptop, CLEVO_CMD_GET_EVENT, 0, NULL);

	clevo_laptop_event(laptop, event);
}

static void clevo_acpi_remove_notify(void *data)
{
	struct clevo_laptop *laptop = data;

	acpi_dev_remove_notify_handler(ACPI_COMPANION(laptop->dev), ACPI_ALL_NOTIFY,
				       clevo_acpi_notify);
}

static int clevo_acpi_probe(struct platform_device *pdev)
{
	struct acpi_device *adev = ACPI_COMPANION(&pdev->dev);
	struct clevo_laptop *laptop;
	int ret;

	if (!adev)
		return -ENODEV;

	laptop = clevo_laptop_probe(&pdev->dev, &clevo_acpi_transport);
	if (IS_ERR(laptop))
		return PTR_ERR(laptop);

	if (!laptop->input)
		return 0;

	ret = acpi_dev_install_notify_handler(adev, ACPI_ALL_NOTIFY,
					      clevo_acpi_notify, laptop);
	if (ret)
		return ret;

	/* Runs before the LED and the input device are released. */
	ret = devm_add_action_or_reset(&pdev->dev, clevo_acpi_remove_notify, laptop);
	if (ret)
		return ret;

	clevo_laptop_enable_events(laptop);
	return 0;
}

static const struct acpi_device_id clevo_acpi_ids[] = {
	{ CLEVO_ACPI_HID },
	{ }
};
MODULE_DEVICE_TABLE(acpi, clevo_acpi_ids);

static struct platform_driver clevo_acpi_driver = {
	.driver = {
		.name = "clevo-control",
		.acpi_match_table = clevo_acpi_ids,
		.pm = pm_sleep_ptr(&clevo_pm_ops),
	},
	.probe = clevo_acpi_probe,
};

/*
 * WMI back-end, for models without CLV0001: commands through the method
 * device, hotkeys through the event device.
 *
 * wmidev_evaluate_method() and the .notify callback are the only WMI calls
 * available on every kernel this module supports (6.14 and later); their
 * successors exist from 7.0 only.
 */

/* The method device's laptop, for the event device. Protected by the mutex. */
static struct clevo_laptop *clevo_wmi_laptop;
static DEFINE_MUTEX(clevo_wmi_lock);

/* On success *obj is the reply, possibly NULL, to be released with kfree(). */
static int clevo_wmi_evaluate(struct device *dev, u32 cmd, u32 arg,
			      union acpi_object **obj)
{
	struct acpi_buffer in = { .length = sizeof(arg), .pointer = &arg };
	struct acpi_buffer out = { .length = ACPI_ALLOCATE_BUFFER };
	acpi_status status;

	status = wmidev_evaluate_method(to_wmi_device(dev), 0, cmd, &in, &out);
	if (ACPI_FAILURE(status))
		return -EIO;

	*obj = out.pointer;
	return 0;
}

static int clevo_wmi_call(struct device *dev, u32 cmd, u32 arg, u32 *result)
{
	union acpi_object *obj;
	int ret;

	ret = clevo_wmi_evaluate(dev, cmd, arg, &obj);
	if (ret)
		return ret;

	ret = clevo_reply_integer(obj, result);
	kfree(obj);
	return ret;
}

static int clevo_wmi_read(struct device *dev, u32 cmd, u32 arg, u8 *buf, size_t len)
{
	union acpi_object *obj;
	int ret;

	ret = clevo_wmi_evaluate(dev, cmd, arg, &obj);
	if (ret)
		return ret;

	ret = clevo_reply_buffer(obj, buf, len);
	kfree(obj);
	return ret;
}

static const struct clevo_transport clevo_wmi_transport = {
	.call = clevo_wmi_call,
	.read = clevo_wmi_read,
};

static int clevo_wmi_probe(struct wmi_device *wdev, const void *context)
{
	struct clevo_laptop *laptop;

	/* The ACPI device is the preferred interface where it exists. */
	if (acpi_dev_present(CLEVO_ACPI_HID, NULL, -1))
		return -ENODEV;

	laptop = clevo_laptop_probe(&wdev->dev, &clevo_wmi_transport);
	if (IS_ERR(laptop))
		return PTR_ERR(laptop);

	scoped_guard(mutex, &clevo_wmi_lock)
		clevo_wmi_laptop = laptop;

	clevo_laptop_enable_events(laptop);
	return 0;
}

static void clevo_wmi_remove(struct wmi_device *wdev)
{
	/* After this no event can reach the laptop being released. */
	guard(mutex)(&clevo_wmi_lock);
	clevo_wmi_laptop = NULL;
}

static const struct wmi_device_id clevo_wmi_ids[] = {
	{ .guid_string = CLEVO_WMI_METHOD_GUID },
	{ }
};
MODULE_DEVICE_TABLE(wmi, clevo_wmi_ids);

static struct wmi_driver clevo_wmi_driver = {
	.driver = {
		.name = "clevo-control-wmi",
		.pm = pm_sleep_ptr(&clevo_pm_ops),
	},
	.id_table = clevo_wmi_ids,
	.probe = clevo_wmi_probe,
	.remove = clevo_wmi_remove,
};

static void clevo_wmi_event_notify(struct wmi_device *wdev, union acpi_object *data)
{
	u32 event;

	guard(mutex)(&clevo_wmi_lock);

	if (!clevo_wmi_laptop || !clevo_wmi_laptop->input)
		return;

	/* The event itself carries no data; the code has to be fetched. */
	if (clevo_fw_call(clevo_wmi_laptop, CLEVO_CMD_GET_EVENT, 0, &event))
		return;

	clevo_laptop_event(clevo_wmi_laptop, event);
}

static int clevo_wmi_event_probe(struct wmi_device *wdev, const void *context)
{
	return acpi_dev_present(CLEVO_ACPI_HID, NULL, -1) ? -ENODEV : 0;
}

static const struct wmi_device_id clevo_wmi_event_ids[] = {
	{ .guid_string = CLEVO_WMI_EVENT_GUID },
	{ }
};
MODULE_DEVICE_TABLE(wmi, clevo_wmi_event_ids);

static struct wmi_driver clevo_wmi_event_driver = {
	.driver = {
		.name = "clevo-control-wmi-events",
	},
	.id_table = clevo_wmi_event_ids,
	.no_notify_data = true,
	.probe = clevo_wmi_event_probe,
	.notify = clevo_wmi_event_notify,
};

static int __init clevo_init(void)
{
	int ret;

	ret = platform_driver_register(&clevo_acpi_driver);
	if (ret)
		return ret;

	ret = wmi_driver_register(&clevo_wmi_driver);
	if (ret)
		goto err_acpi;

	ret = wmi_driver_register(&clevo_wmi_event_driver);
	if (ret)
		goto err_wmi;

	return 0;

err_wmi:
	wmi_driver_unregister(&clevo_wmi_driver);
err_acpi:
	platform_driver_unregister(&clevo_acpi_driver);
	return ret;
}
module_init(clevo_init);

static void __exit clevo_exit(void)
{
	wmi_driver_unregister(&clevo_wmi_event_driver);
	wmi_driver_unregister(&clevo_wmi_driver);
	platform_driver_unregister(&clevo_acpi_driver);
}
module_exit(clevo_exit);

MODULE_AUTHOR("Pavel Nikanovich <pavelnikanovich@gmail.com>");
MODULE_DESCRIPTION("Clevo laptop keyboard backlight, hotkeys and performance profiles");
MODULE_LICENSE("GPL");
