# P1 Serial Source

This script sends raw P1 Belgian and Dutch electricity meter frames from a serial device (e.g. a USB adapter such as ) to an MQTT broker in a format that can be processed by the [P1 Cookie Parser](https://gitlab.com/Epyon01P/p1-cookie-parser).

## Installation

Clone this repository, adjust settings in `p1config.yaml` and run

```bash
python p1publisher.py
```
