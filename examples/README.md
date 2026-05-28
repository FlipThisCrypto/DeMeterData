# examples/ — Copy/paste templates for extending The Orchard

The point of this folder: lower the barrier for a novice to extend the project. If you've never written a sensor driver, copy a template, fill in the blanks, and you're done.

## What's here

- **sensor_driver/** — A blank ESP32 sensor driver in the modular firmware style. Copy into `firmware/src/sensors/` and rename.
- **wiring/** — A wiring documentation template for new sensors. Copy into `docs/wiring/`.

> More templates will be added as the project grows: node-type variants (PoE, battery+solar), radio modules (LoRa, cellular), dashboard plugins, etc.

## How to use

1. Pick the template that matches what you want to add.
2. Copy it to the appropriate destination folder (`firmware/src/sensors/`, `docs/wiring/`, etc.).
3. Rename and fill in the blanks.
4. Open a PR. See [../CONTRIBUTING.md](../CONTRIBUTING.md).

Every template includes inline comments explaining each section.
