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

# report start time
startTime = "2024-09-01T00:00:00.000Z"

# report end time
endTime = "2024-09-08T00:00:00.000Z"



##############################################################################
# Shouldn't need to edit below here for normal use.

from pprint import pprint
import requests
import json
import os
import sys

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
            #print(result['id'])
            case_id_list.append(result['id'])
    else:
        print(f"Error: {response.status_code} - {response.text}")

    return case_id_list


def sum_hours_saved_by_case_id(case_id):
    url = f"{base_url}/api/external/v1/dynamic-cases/GetCaseDetails/{case_id}"
    headers = {
        'accept': 'application/json;odata.metadata=minimal;odata.streaming=true',
        'AppKey': app_key,
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        json_data = response.json()
        #pprint(json_data)
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

    #clear_screen()
    print()
    pprint(roi_counts)


def clear_screen():
  """Clears the terminal screen."""
  os.system('cls' if os.name == 'nt' else 'clear')

if __name__ == '__main__':
    for case_id in get_case_ids():
        sum_hours_saved_by_case_id(case_id)
    print("\n\n\nHours saved by playbook:\n")
    pprint(roi_counts)

