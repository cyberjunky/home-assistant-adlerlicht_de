[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
![Project Maintenance][maintenance-shield]

[![Donate via PayPal](https://img.shields.io/badge/Donate-PayPal-blue.svg?style=for-the-badge&logo=paypal)](https://www.paypal.me/cyberjunkynl/)
[![Sponsor on GitHub](https://img.shields.io/badge/Sponsor-GitHub-red.svg?style=for-the-badge&logo=github)](https://github.com/sponsors/cyberjunky)

<img src="custom_components/adlerlicht_de/brand/icon.png" alt="Adlerlicht" width="128" align="right">

# Adlerlicht Integration

A Home Assistant custom integration that brings German police reports ("Blaulichtmeldungen") from [adlerlicht.de](https://adlerlicht.de) into Home Assistant, for one or more cities of your choice.

Every report the site has geocoded becomes a marker on your Home Assistant map, and each city gets sensors summarising its reports plus an event entity you can trigger notifications from.

## Supported Features

- **Map markers**: each report becomes a `geo_location` entity with its real coordinates
- **Sensors**: number of current reports, the newest report and its category
- **Event entity**: triggers for every newly published report, ready for notifications
- **Bus event**: `adlerlicht_de_new_report` for automations that prefer an event trigger
- **GUI configuration**: city lookup through the site's own search, no YAML required
- **Filters**: by category, by distance from your home location, and by number of reports
- **Multiple cities**: add the integration once per city you want to follow

> [!NOTE]
> adlerlicht.de has no public API. This integration reads the same data the city pages
> themselves render, and polls **once every 15 minutes** to stay a considerate guest.
> Only cities that have their own page on adlerlicht.de can be followed.

## Entities

Each configured city becomes a device with these entities, where `<city>` is the city name:

| Entity | Type | State |
|--------|------|-------|
| `sensor.<city>_reports` | Sensor | Number of reports currently matching your filters |
| `sensor.<city>_latest_report` | Timestamp | Publication time of the newest report |
| `sensor.<city>_latest_category` | Enum | Category of the newest report, in German |
| `event.<city>_new_report` | Event | Triggers on every newly published report |
| `geo_location.<report title>` | Geolocation | Distance from home, one entity per report |

### Report Attributes

The geolocation entities, `sensor.<city>_latest_report` and the event entity all carry the
details of a report:

| Attribute | Description |
|-----------|-------------|
| `external_id` | Report id on adlerlicht.de |
| `title` | Headline of the report |
| `summary` | Short summary of what happened |
| `category` | Primary category, in German (e.g. `Einbruch`) |
| `category_key` | Primary category key (e.g. `burglary`) |
| `categories` | All category keys of the report |
| `location` | Street or district the site reported, when known |
| `city` | The configured city (geolocation entities only) |
| `publication_date` | When the report was published |
| `incident_date` | When the incident happened, when known |
| `incident_time` | Time of the incident, when known |
| `latitude` / `longitude` | Coordinates of the report |
| `url` | Link to the full report on adlerlicht.de |

`sensor.<city>_reports` additionally exposes a `reports` attribute holding every current
report as a list, plus a count per category (for example `Verkehr: 4`).

### Categories

adlerlicht.de classifies reports into these categories:

| Key | German label | Key | German label |
|-----|--------------|-----|--------------|
| `arson` | Brandstiftung | `murder` | Tötungsdelikt |
| `assault` | Körperverletzung | `other` | Sonstiges |
| `burglary` | Einbruch | `public_order` | Öffentliche Ordnung |
| `drugs` | Drogen | `robbery` | Raub |
| `environmental` | Umwelt | `sexual` | Sexualdelikt |
| `extremism` | Extremismus | `theft` | Diebstahl |
| `fraud` | Betrug | `traffic` | Verkehr |
| `knife` | Messer | `vandalism` | Sachbeschädigung |
| `missing` | Vermisst | `weapons` | Waffen |

## Installation

### HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=cyberjunky&repository=home-assistant-adlerlicht_de&category=integration)

Alternatively:

1. Ensure [HACS](https://hacs.xyz) is installed
2. Search for "Adlerlicht" in HACS
3. Click **Download**
4. Restart Home Assistant
5. Add via Settings → Devices & Services

### Manual Installation

1. Copy the `custom_components/adlerlicht_de` folder to your `<config>/custom_components/` directory
2. Restart Home Assistant
3. Add via Settings → Devices & Services

## Configuration

### GUI Setup

1. Go to **Settings → Devices & Services**
2. Click **+ Add Integration**
3. Search for "Adlerlicht"
4. Type the name of the city you want to follow, for example `Gera`
5. If several cities match, pick the right one from the list
6. Click Submit

Repeat for every city you want to follow.

### Configuration Options

Open **Settings → Devices & Services → Adlerlicht → Configure**:

| Option | Default | Description |
|--------|---------|-------------|
| **Categories** | All | Only keep reports in these categories |
| **Radius around home** | 0 (no limit) | Only keep reports within this many kilometres of your home location |
| **Maximum number of reports** | 20 | How many of the newest reports to expose as entities (1-80) |

> [!NOTE]
> The radius is measured from the home location in your Home Assistant settings.
> It is useful for big cities: a report on the other side of town is rarely interesting.

## Map Card

The geolocation entities appear on the default map automatically. To get a dedicated card
showing only police reports:

```yaml
type: map
geo_location_sources:
  - adlerlicht_de
hours_to_show: 24
auto_fit: true
```

## Automation Examples

### Notify on Every New Report

The event entity is the simplest trigger — it fires once per newly published report:

```yaml
alias: "Adlerlicht: new report"
triggers:
  - trigger: state
    entity_id: event.gera_new_report
conditions:
  # Ignore the "unknown" state the entity has before the first report.
  - condition: template
    value_template: "{{ trigger.to_state.state not in ['unknown', 'unavailable'] }}"
actions:
  - action: notify.mobile_app_phone
    data:
      title: "{{ state_attr('event.gera_new_report', 'category') }} in Gera"
      message: "{{ state_attr('event.gera_new_report', 'title') }}"
      data:
        url: "{{ state_attr('event.gera_new_report', 'url') }}"
mode: queued
```

### Notify Only for Selected Categories

The event type is the category key, so you can filter on it directly:

```yaml
alias: "Adlerlicht: burglaries only"
triggers:
  - trigger: state
    entity_id: event.gera_new_report
conditions:
  - condition: template
    value_template: >
      {{ state_attr('event.gera_new_report', 'category_key')
         in ['burglary', 'robbery', 'theft'] }}
actions:
  - action: notify.mobile_app_phone
    data:
      title: "Einbruch/Diebstahl in Gera"
      message: "{{ state_attr('event.gera_new_report', 'title') }}"
mode: queued
```

### Notify Using the Bus Event

Every new report is also fired on the event bus, which is handy when you follow several
cities with a single automation:

```yaml
alias: "Adlerlicht: any city"
triggers:
  - trigger: event
    event_type: adlerlicht_de_new_report
conditions: []
actions:
  - action: notify.mobile_app_phone
    data:
      title: "{{ trigger.event.data.category }} in {{ trigger.event.data.city }}"
      message: >
        {{ trigger.event.data.title }}
        ({{ trigger.event.data.location }})
      data:
        url: "{{ trigger.event.data.url }}"
mode: queued
```

### Notify Only Close to Home

`geo_location` entities have the distance from home as their state, so you can react to
anything that appears nearby:

```yaml
alias: "Adlerlicht: report nearby"
triggers:
  - trigger: event
    event_type: adlerlicht_de_new_report
conditions:
  - condition: template
    value_template: >
      {{ distance(trigger.event.data.latitude, trigger.event.data.longitude) | float(999) < 2 }}
actions:
  - action: notify.mobile_app_phone
    data:
      title: "Meldung in der Nähe ({{ trigger.event.data.category }})"
      message: "{{ trigger.event.data.title }}"
mode: queued
```

### Daily Summary

```yaml
alias: "Adlerlicht: daily summary"
triggers:
  - trigger: time
    at: "19:00:00"
conditions:
  - condition: numeric_state
    entity_id: sensor.gera_reports
    above: 0
actions:
  - action: notify.mobile_app_phone
    data:
      title: "Gera: {{ states('sensor.gera_reports') }} Meldungen"
      message: >
        {% for report in state_attr('sensor.gera_reports', 'reports')[:5] %}
        - {{ report.category }}: {{ report.title }}
        {% endfor %}
mode: single
```

### Template Sensor: Reports in the Last 24 Hours

```yaml
# configuration.yaml
template:
  - sensor:
      - name: "Gera reports today"
        unique_id: gera_reports_today
        state: >
          {{ state_attr('sensor.gera_reports', 'reports') | default([], true)
             | map(attribute='publication_date') | select('string')
             | map('as_datetime')
             | select('>=', now() - timedelta(hours=24))
             | list | count }}
        unit_of_measurement: "reports"
```

## Troubleshooting

### No city found

Only cities with their own page on adlerlicht.de can be followed. Smaller places are
covered by the site but have no page of their own, and the setup form will say so. Try the
nearest larger city, or search for the place on adlerlicht.de first to see whether it has a
page.

### No entities appear

The integration only creates entities for reports adlerlicht.de has geocoded. Reports
without coordinates cannot be placed on a map and are skipped. If your filters are strict
(a small radius combined with a few categories) it is normal to end up with nothing.

### Notifications fire for old reports after a restart

They should not: the reports already present at the first refresh after a restart are
recorded as seen and do not trigger the event entity or the bus event. Only reports that
appear afterwards do.

### Enable Debug Logging

Enable debug logging in `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.adlerlicht_de: debug
```

Alternatively enable debug logging via **Settings** → **Devices & Services** → **Adlerlicht**
→ **Enable debug logging**, reproduce the issue, and disable it again to download the log.

## Development

Quick-start (from project root):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements_lint.txt
./scripts/lint      # runs pre-commit + vulture
pytest              # runs the test suite
./scripts/develop   # starts Home Assistant with this integration loaded
```

The repository also ships a devcontainer: open it in VS Code, and `scripts/setup` installs
Home Assistant and the lint tooling for you. Home Assistant is then reachable on port 8123.

## Disclaimer

This integration is not affiliated with adlerlicht.de. The reports it shows are published by
German police forces and processed by adlerlicht.de; their accuracy and completeness are
outside the control of this integration. Coordinates are approximations made by the site,
often only precise to the street.

## 💖 Support This Project

If you find this integration useful, please consider supporting its continued development and maintenance:

### 🌟 Ways to Support

- **⭐ Star this repository** - Help others discover the project
- **💰 Financial Support** - Contribute to development and hosting costs
- **🐛 Report Issues** - Help improve stability and compatibility
- **📖 Spread the Word** - Share with other Home Assistant users

### 💳 Financial Support Options

[![Donate via PayPal](https://img.shields.io/badge/Donate-PayPal-blue.svg?style=for-the-badge&logo=paypal)](https://www.paypal.me/cyberjunkynl/)
[![Sponsor on GitHub](https://img.shields.io/badge/Sponsor-GitHub-red.svg?style=for-the-badge&logo=github)](https://github.com/sponsors/cyberjunky)

Every contribution, no matter the size, makes a difference and is greatly appreciated! 🙏

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

[releases-shield]: https://img.shields.io/github/release/cyberjunky/home-assistant-adlerlicht_de.svg?style=for-the-badge
[releases]: https://github.com/cyberjunky/home-assistant-adlerlicht_de/releases
[commits-shield]: https://img.shields.io/github/commit-activity/y/cyberjunky/home-assistant-adlerlicht_de.svg?style=for-the-badge
[commits]: https://github.com/cyberjunky/home-assistant-adlerlicht_de/commits/main
[license-shield]: https://img.shields.io/github/license/cyberjunky/home-assistant-adlerlicht_de.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-cyberjunky-blue.svg?style=for-the-badge
