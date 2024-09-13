#!/usr/bin/env python3
#
# This script calculates the amount of analyst time saved with Google SOAR based
# on playbook execution volume and a map of time saved by playbook title.
#
# It expects:
#      SOAR API key in the APP_KEY environment variable
#      SOAR API base URL in the BASE_URL environment variable
#
# Please send bugs to: jmarts@google.com
#
# Example output:
#
#  Hours saved by playbook:
#
#  {'Copy of Enrich Falcon Alerts': 6004,
#   'Enrich Defender 365 Alerts': 3007,
#   'Enrich Defender ATP Alerts': 420,
#   'Enrich Falcon Alerts': 5,
#   'Enrich FireEye Alerts': 875,
#   'Enrich Rapid7  Alerts': 3840}
#

##############################################################################
# EDIT HERE

# Minutes saved per playbook execution indexed by playbook name. Any playbook
# executions that don't have an entry here will be assigned the value of the
# __unconfigured__ key.
playbook_time_def_map = {
    "Enrich Defender ATP Alerts": 30,
    "Enrich Falcon Alerts": 5,
    "Enrich FireEye Alerts": 25,
    "Enrich Rapid7  Alerts": 60,
    "__unconfigured__": 10,
}

##############################################################################
# Shouldn't need to edit below here for normal use.

from pprint import pprint
import requests
import json
import os
import sys
import datetime
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
import time


# Check for required environment variables
required_env_vars = ['APP_KEY', 'BASE_URL']
missing_vars = [var for var in required_env_vars if os.environ.get(var) is None]

if missing_vars:
    error_message = f"Error: The following environment variables are missing: {', '.join(missing_vars)}"
    print(error_message, file=sys.stderr)  # Print to stderr for error messages
    sys.exit(1)  # Exit with a non-zero status code to indicate an error

# Get AppKey from environment variable
app_key = os.environ.get('APP_KEY')

# Your SOAR instance base URL
base_url = os.environ.get('BASE_URL', 'https://acme-01.siemplify-soar.com')  # Default if not set

headers = {
    'accept': 'application/json;odata.metadata=minimal;odata.streaming=true',
    'AppKey': app_key,
    'Content-Type': 'application/json;odata.metadata=minimal;odata.streaming=false'
}

# runtime ROI counts
roi_counts = {}


def get_case_ids():
    url = f'{base_url}/api/external/v1/search/CaseSearchEverything'
    data = {
        "tags": [],
        "ruleGenerator": [],
        "caseSource": [],
        "stage": [],
        "environments": [],
        "assignedUsers": [],
        "products": [],
        "ports": [],
        "categoryOutcomes": [],
        "status": [],
        "caseIds": [],
        "incident": [],
        "importance": [],
        "priorities": [],
        "pageSize": 99999,
        "title": "",
        "startTime": startTime,
        "endTime": endTime,
        "requestedPage": 0,
        "timeRangeFilter": 0
    }

    response = requests.post(url, headers=headers, json=data)

    case_id_list = []

    if response.status_code == 200:
        json_data = response.json()
        for result in json_data['results']:
            # print(result['id'])
            case_id_list.append(result['id'])
    else:
        print(f"Error: {response.status_code} - {response.text}")

    return case_id_list


def sum_minutes_saved_by_case_id(case_id):
    url = f"{base_url}/api/external/v1/dynamic-cases/GetCaseDetails/{case_id}"
    headers = {
        'accept': 'application/json;odata.metadata=minimal;odata.streaming=true',
        'AppKey': app_key,
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        json_data = response.json()
        # pprint(json_data)
        playbook_attached_list = [alert_card['playbookAttached'] for alert_card in json_data['alertCards']]
        for pb in playbook_attached_list:
            try:
                if pb in roi_counts:
                    roi_counts[pb] += playbook_time_def_map[pb]
                else:
                    try:
                        roi_counts[pb] = playbook_time_def_map[pb]
                    except KeyError:
                        roi_counts[pb] = playbook_time_def_map['__unconfigured__']
            except Exception:
                roi_counts[pb] += 999
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

    print()
    pprint(roi_counts)


if __name__ == '__main__':
    all_roi_counts = {}  # Store ROI counts for all days
    total_minutes_saved = {}  # Store total minutes saved per playbook

    for i in range(3):  # Loop over the last 3 days
        # Calculate start and end times for each day
        end_date = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - datetime.timedelta(days=i + 1)  # Adjust for 0-based indexing

        startTime = start_date.isoformat() + "Z"
        endTime = end_date.isoformat() + "Z"

        roi_counts = {}  # Reset roi_counts for each day
        for case_id in get_case_ids():
            time.sleep(1.6)
            sum_minutes_saved_by_case_id(case_id)

        all_roi_counts[start_date.strftime("%Y-%m-%d")] = roi_counts

        # Update total minutes saved per playbook
        for playbook, minutes in roi_counts.items():
            if playbook in total_minutes_saved:
                total_minutes_saved[playbook] += minutes
            else:
                total_minutes_saved[playbook] = minutes

    # Prepare data for Seaborn bar chart
    data = []
    for day, counts in all_roi_counts.items():
        for playbook, minutes in counts.items():
            data.append({"Day": day, "Playbook": playbook, "Minutes Saved": minutes})

    df = pd.DataFrame(data)

    # Create the bar chart
    plt.figure(figsize=(12, 6))  # Adjust figure size as needed
    sns.barplot(x="Day", y="Minutes Saved", hue="Playbook", data=df, palette='YlGnBu')
    plt.title("Minutes Saved by Playbook Over the Last 3 Days")
    plt.xticks(rotation=45, ha="right")  # Rotate x-axis labels for better readability
    plt.tight_layout()
    plt.show()

    # Print numeric summary of total minutes saved
    print("\nTotal Minutes Saved per Playbook:")
    for playbook, minutes in total_minutes_saved.items():
        print(f"{playbook}: {minutes}")

    # Create the pie chart
    plt.figure(figsize=(8, 8))
    colors = sns.color_palette("YlGnBu", n_colors=len(total_minutes_saved))  # Create a list of colors from the YlGnBu palette
    plt.pie(total_minutes_saved.values(), labels=total_minutes_saved.keys(), autopct='%1.1f%%', startangle=90, colors=colors)
    plt.title("Total Minutes Saved per Playbook")
    plt.show()
