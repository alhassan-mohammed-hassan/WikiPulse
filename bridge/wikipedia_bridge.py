import json
import logging
import os
import time

import requests

# Configuration
WIKIPEDIA_STREAM_URL = (
    "https://stream.wikimedia.org/v2/stream/recentchange"
)

NIFI_URL = os.getenv(
    "NIFI_URL",
    "http://nifi:8081/contentListener"
)

USER_AGENT = "WikiPulse/1.0 (Wikipedia Activity Monitoring Project)"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

session = requests.Session()
session.headers.update({
    "User-Agent": USER_AGENT
})


def send_to_nifi(event):
    """Forward one Wikipedia event to NiFi."""

    try:
        response = session.post(
            NIFI_URL,
            json=event,
            timeout=10
        )

        response.raise_for_status()

        logging.info(
            "Event forwarded to NiFi successfully. Status: %s",
            response.status_code
        )

    except requests.RequestException as error:
        logging.error("Failed to send event to NiFi: %s", error)


def consume_events():
    """Consume Wikipedia SSE events and forward them to NiFi."""

    retry_delay = 5

    while True:
        try:
            logging.info("Connecting to Wikipedia EventStreams...")

            with session.get(
                WIKIPEDIA_STREAM_URL,
                stream=True,
                headers={"Accept": "text/event-stream"},
                timeout=(15, 90)
            ) as response:

                response.raise_for_status()

                logging.info("Connected to Wikipedia EventStreams.")

                retry_delay = 5

                for line in response.iter_lines(decode_unicode=True):

                    if not line or not line.startswith("data:"):
                        continue

                    raw_data = line[5:].strip()

                    try:
                        event = json.loads(raw_data)
                        send_to_nifi(event)

                    except json.JSONDecodeError:
                        logging.warning("Invalid JSON event received.")

        except requests.RequestException as error:
            logging.error("Connection error: %s", error)

        logging.info("Reconnecting in %s seconds...", retry_delay)
        time.sleep(retry_delay)
        retry_delay = min(retry_delay * 2, 60)


if __name__ == "__main__":
    consume_events()