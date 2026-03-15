import requests
import logging
import sys
import json
from os import environ
from dotenv import load_dotenv

CLOUDFLARE_API_KEY = ""


def public_ip() -> str:
    ip = ""

    try:
        response = requests.get("https://api64.ipify.org/")
        ip = response.text
    except requests.RequestException as e:
        logging.error(f"Error fetching IP: {e}")
    finally:
        return ip


def fetch_cloudflare_records(zone_id: str) -> dict | None:
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"

    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers)
    logging.info(
        f"HTTP/1.1 - {response.status_code} {response.reason} - GET {url}")

    if response.status_code != 200:
        return None

    return response.json()


def notify_cloudflare_dns(
    domain: str, zone_id: str, dns_record_id: str, ip: str
) -> bool:
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{
        dns_record_id
    }"

    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "type": "A",
        "name": domain,
        "content": ip,
    }

    response = requests.put(url, headers=headers, json=data)
    logging.info(
        f"HTTP/1.1 - {response.status_code} {response.reason} - PUT {url}")

    if response.status_code != 200:
        logging.error(f"Response: {response.text}")

    return response.status_code == 200


def update_each_domain(domain: str, zone_id: str, record_id: str, ip: str):
    dns_records = fetch_cloudflare_records(zone_id)

    if dns_records is None:
        logging.error("Failed to fetch DNS Records")
        return

    if len(dns_records["result"]) == 0:
        logging.warning("No DNS Record was found.")
        return

    records = dns_records["result"]
    records = [x for x in records if x["name"] == domain]

    if len(records) == 0:
        logging.warning(
            "No DNS Record was found for the specified domain name.")
        return

    record_ip = records[0]["content"]

    if record_ip == ip:
        logging.info(
            f"Domain IP is up-to-date. IP: {ip} | Record IP: {record_ip}")
        return

    is_updated = notify_cloudflare_dns(domain, zone_id, record_id, ip)

    if is_updated:
        return

    logging.error("Failed to update DNS Record")


def main():
    ip = public_ip()

    if ip == "":
        return

    logging.info(f"Current found IP: {ip}")

    domains = json.loads(environ.get("DOMAINS"))

    for domain in domains:
        update_each_domain(
            domain["domain"], domain["zone_id"], domain["dns_record_id"], ip
        )


if __name__ == "__main__":
    load_dotenv()

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
    )
    CLOUDFLARE_API_KEY = environ.get("CLOUDFLARE_API_TOKEN")
    main()
