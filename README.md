# Arrowhead Alarm Library

![Python Versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)
![CI](https://github.com/Eclipse7899/arrowhead_alarm/actions/workflows/python-test.yml/badge.svg)
![Codecov](https://img.shields.io/codecov/c/github/Eclipse7899/arrowhead_alarm)

## Feature Overview

- Area arming/disarming
- Zone monitoring
- Output control

## Installation Instructions

### Requirements

- Python 3.10 or higher

### Installation

```
pip install arrowhead-alarm
```

## Usage Instructions

```python
from arrowhead_alarm import Mode1Client, ArmingMode, LoginCredentials


async def main():
    client = Mode1Client(
        host="192.168.0.20",
        port=9000,
        credentials=LoginCredentials("username", "password")
    ),

    await client.connect()
    await client.arm_button(ArmingMode.AWAY)

```

