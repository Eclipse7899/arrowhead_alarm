# Arrowhead Alarm Library

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
from arrowhead_alarm import create_mode_2_client, ArmingMode


async def main():
    client = create_mode_2_client(
        host="192.168.0.20",
        port=9000,
        username="admin",
        password="admin"
    )

    await client.connect()
    await client.arm_area(1, ArmingMode.AWAY)

```

