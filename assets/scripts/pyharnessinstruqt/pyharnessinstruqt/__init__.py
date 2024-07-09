"""
Python module used during the instantiation of Instruqt workshop environments

"""

import os
import pwd
import grp
import subprocess
import time
import requests
from jinja2 import Template
import json
import random
import hashlib
from kubernetes import client, utils
import yaml

#### GLOBAL VARIABLES ####
HARNESS_API = "https://app.harness.io"


#### HARNESS FUNCTIONS ####
def verify_harness_login(api_key, account_id, user_name):
    """
    Verifies the login of a user in Harness by checking the audit logs.

    :param api_key: The API key for accessing Harness API.
    :param account_id: The account ID in Harness.
    :param user_name: The user name to verify the login for.
    :return: True if the user has logged in, otherwise False.
    """
    time_filter = int(time.time() * 1000) - 300000  # Current time in milliseconds minus 5 minutes

    print(f"Validating Harness login for user '{user_name}'...")
    url = f"{HARNESS_API}/gateway/audit/api/audits/list?accountIdentifier={account_id}"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }
    payload = {
        "actions": ["LOGIN"],
        "principals": [{
            "type": "USER",
            "identifier": user_name
        }],
        "filterType": "Audit",
        "startTime": str(time_filter)
    }

    response = requests.post(url, headers=headers, json=payload)
    response_data = response.json()
    response_items = response_data.get("data", {}).get("totalItems", 0)

    if response_items >= 1:
        print("Successful login found in audit trail.")
        return True
    else:
        print("No Logins were found in the last 5 minutes")
        return False


def create_harness_project(api_key, account_id, org_id, project_name):
    """
    Creates a project in Harness.

    :param api_key: The API key for accessing Harness API.
    :param account_id: The account ID in Harness.
    :param org_id: The organization ID in Harness.
    :param project_name: The name of the project to create.
    """
    url = f"{HARNESS_API}/gateway/ng/api/projects?accountIdentifier={account_id}&orgIdentifier={org_id}"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }
    payload = {
        "project": {
            "name": project_name,
            "orgIdentifier": org_id,
            "description": "Automated build via Instruqt.",
            "identifier": project_name,
            "tags": {
                "automated": "yes",
                "owner": "instruqt"
            }
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    response_data = response.json()
    response_status = response_data.get("status")

    if response_status == "SUCCESS":
        print(f"Project '{project_name}' created successfully.")
    else:
        print(f"Failed to create project '{project_name}'. Response: {response_data}")
        raise SystemExit(1)


def invite_user_to_harness_project(api_key, account_id, org_id, project_id, user_email):
    """
    Invites a user to a Harness project.

    :param api_key: The API key for accessing Harness API.
    :param account_id: The account ID in Harness.
    :param org_id: The organization ID in Harness.
    :param project_id: The project ID in Harness.
    :param user_email: The email of the user to invite.
    """
    url = f"{HARNESS_API}/gateway/ng/api/user/users?accountIdentifier={account_id}&orgIdentifier={org_id}&projectIdentifier={project_id}"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }
    payload = {
        "emails": [user_email],
        "userGroups": ["_project_all_users"],
        "roleBindings": [{
            "resourceGroupIdentifier": "_all_project_level_resources",
            "roleIdentifier": "_project_admin",
            "roleName": "Project Admin",
            "resourceGroupName": "All Project Level Resources",
            "managedRole": True
        }]
    }

    response = requests.post(url, headers=headers, json=payload)
    return response.json()


def invite_user_to_harness_project_loop(api_key, account_id, org_id, project_id, user_email):
    """
    Invites a user to a Harness project with retry logic.

    :param api_key: The API key for accessing Harness API.
    :param account_id: The account ID in Harness.
    :param org_id: The organization ID in Harness.
    :param project_id: The project ID in Harness.
    :param user_email: The email of the user to invite.
    """
    max_attempts = 4
    invite_attempts = 0

    print("Inviting the user to the project...")
    invite_response = invite_user_to_harness_project(api_key, account_id, org_id, project_id, user_email)
    invite_status = invite_response.get("status")
    print(f"  DEBUG: Status: {invite_status}")

    while invite_status != "SUCCESS" and invite_attempts < max_attempts:
        print(f"User invite to project has failed. Retrying... Attempt: {invite_attempts + 1}")
        invite_response = invite_user_to_harness_project(api_key, account_id, org_id, project_id, user_email)
        invite_status = invite_response.get("status")
        print(f"  DEBUG: Status: {invite_status}")
        invite_attempts += 1
        time.sleep(3)

    if invite_status == "SUCCESS":
        print("The API hit worked, your user was invited successfully.")
    else:
        print(f"API hit to invite the user to the project has failed after {max_attempts} attempts. Response: {invite_response}")
        raise SystemExit(1)


def delete_harness_project(api_key, account_id, org_id, project_id, cleanup=False):
    """
    Deletes a project in Harness.

    :param api_key: The API key for accessing Harness API.
    :param account_id: The account ID in Harness.
    :param org_id: The organization ID in Harness.
    :param project_id: The project ID to delete.
    :param cleanup: Flag to continue the cleanup process on failure.
    """
    url = f"{HARNESS_API}/gateway/ng/api/projects/{project_id}?accountIdentifier={account_id}&orgIdentifier={org_id}"
    headers = {
        "x-api-key": api_key
    }

    response = requests.delete(url, headers=headers)
    response_data = response.json()
    response_status = response_data.get("status")

    if response_status == "SUCCESS":
        print(f"Project '{project_id}' deleted successfully.")
    else:
        print(f"Failed to delete project '{project_id}'. Response: {response_data}")
        if cleanup:
            print("Attempting to continue the cleanup process...")
        else:
            raise SystemExit(1)


def get_harness_user_id(api_key, account_id, search_term):
    """
    Gets the Harness user ID based on the search term.

    :param api_key: The API key for accessing Harness API.
    :param account_id: The account ID in Harness.
    :param search_term: The term to search for the user.
    :return: The user ID if found, otherwise None.
    """
    url = f"{HARNESS_API}/gateway/ng/api/user/aggregate?accountIdentifier={account_id}&searchTerm={search_term}"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }

    response = requests.post(url, headers=headers)
    response_data = response.json()
    user_id = response_data.get('data', {}).get('content', [{}])[0].get('user', {}).get('uuid')

    print(f"Harness User ID: {user_id}")
    return user_id


def delete_harness_user(api_key, account_id, user_email, cleanup=False):
    """
    Deletes a user from Harness based on their email.

    :param api_key: The API key for accessing Harness API.
    :param account_id: The account ID in Harness.
    :param user_email: The email of the user to delete.
    :param cleanup: Flag to continue the cleanup process on failure.
    """
    user_id = get_harness_user_id(api_key, account_id, user_email)
    if user_id == "null":
        print("Failed to determine the User ID.")
    else:
        print(f"Deleting Harness User ID: {user_id}")
        url = f"{HARNESS_API}/gateway/ng/api/user/{user_id}?accountIdentifier={account_id}"
        headers = {
            "x-api-key": api_key
        }

        response = requests.delete(url, headers=headers)
        response_data = response.json()
        response_status = response_data.get("status")

        if response_status == "SUCCESS":
            print("User deleted successfully.")
        else:
            print(f"Failed to delete user. Response: {response_data}")
            if cleanup:
                print("Attempting to continue the cleanup process...")
            else:
                raise SystemExit(1)


def create_harness_delegate(api_key, account_id, org_id, project_id):
    """
    Creates a project-level delegate in Harness.

    :param api_key: The API key for accessing Harness API.
    :param account_id: The account ID in Harness.
    :param org_id: The organization ID in Harness.
    :param project_id: The project ID in Harness.
    """
    url = f"{HARNESS_API}/gateway/ng/api/download-delegates/kubernetes?accountIdentifier={account_id}&orgIdentifier={org_id}&projectIdentifier={project_id}"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }
    payload = {
        "name": "instruqt-workshop-delegate",
        "description": "Automatically created for this lab",
        "clusterPermissionType": "CLUSTER_ADMIN"
    }

    response = requests.post(url, headers=headers, json=payload, stream=True)
    response_code = response.status_code

    with open("instruqt-delegate.yaml", "wb") as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)

    if 200 <= response_code < 300:
        with open("instruqt-delegate.yaml", 'r') as file:
            validate_yaml_content(file)

        try:
            subprocess.run(["kubectl", "apply", "-f", "instruqt-delegate.yaml"], check=True)
        except subprocess.CalledProcessError:
            print("  ERROR: Failed to apply the provided YAML.")
    else:
        print(f"  ERROR: Request failed. Status Code: {response_code}")


def create_harness_pipeline(api_key, account_id, org_id, project_id, pipeline_yaml):
    """
    Creates a pipeline in the provided Harness project.

    :param api_key: The API key for accessing Harness API.
    :param account_id: The account ID in Harness.
    :param org_id: The organization ID in Harness.
    :param project_id: The project ID in Harness.
    :param pipeline_yaml: The Harness pipeline YAML payload.
    """
    url = f"{HARNESS_API}/pipeline/api/pipelines/v2?accountIdentifier={account_id}&orgIdentifier={org_id}&projectIdentifier={project_id}"
    headers = {
        "Content-Type": "application/yaml",
        "x-api-key": api_key
    }

    validate_yaml_content(pipeline_yaml)
    response = requests.post(url, headers=headers, json=pipeline_yaml, stream=True)
    response_code = response.status_code

    if 200 <= response_code < 300:
        print("  INFO: Successfully created Harness pipeline.")
    else:
        print(f"  ERROR: Request failed. Status Code: {response_code}")


#### HARNESS HCE FUNCTIONS ####
def generate_hce_id(name):
    """
    Generates a probe ID based on the provided name by replacing spaces with underscores and removing dashes.

    :param name: The name to be used for generating the probe ID
    :return: The generated probe ID as a string
    """
    return name.replace(" ", "_").replace("-", "")


def supported_api_methods(request_type):
    """
    Returns the query data for the specified request type.

    :param request_type: The type of request (e.g., 'register_infra', 'add_probe')
    :return: A dictionary containing the mutation, request type, and return fields for the specified request type
    :raises ValueError: If the request type is unsupported
    """
    match request_type:
        case "register_infra":
            return {
                "operation": "mutation",
                "type": "registerInfra",
                "param": {
                    "key": "request",
                    "value": "RegisterInfraRequest!"
                },
                "return": "{ manifest }"
            }
        case "add_probe":
            return {
                "operation": "mutation",
                "type": "addProbe",
                "param": {
                    "key": "request",
                    "value": "ProbeRequest!"
                },
                "return": "{ name type }"
            }
        case "list_infra":
            return {
                "operation": "query",
                "type": "listInfrasV2",
                "param": {
                    "key": "request",
                    "value": "ListInfraRequest"
                },
                "return": "{ totalNoOfInfras infras {infraID name environmentID platformName infraNamespace serviceAccount infraScope installationType} }"
            }
        case "get_infra_manifest":
            return {
                "operation": "query",
                "type": "getInfraManifest",
                "param": {
                    "key": "infraID",
                    "value": "String!"
                },
                "return": ""
            }
        case _:
            raise ValueError(f"Unsupported request type: {request_type}")


def make_api_call(api_key, account_id, org_id, project_id, query_type, request_variables=None):
    """
    Makes an API call to the Chaos API with the specified query type and variables.

    :param api_key: The access token for authentication
    :param account_id: The account identifier
    :param org_id: The organization identifier
    :param project_id: The project identifier
    :param query_type: The type of query to be executed (e.g., 'register_infra', 'add_probe')
    :param request_variables: The variables to be included in the request payload
    :return: The response from the Chaos API as a JSON object
    :raises SystemError: If an HTTP error or other error occurs during the API call
    """
    if request_variables is None:
        request_variables = {}

    query_data = supported_api_methods(query_type)
    chaos_uri = f"{HARNESS_API}/gateway/chaos/manager/api/query"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }

    query = f"""
    {query_data['operation']} {query_data['type']}(${query_data['param']['key']}: {query_data['param']['value']}, $identifiers: IdentifiersRequest!) {{
        {query_data['type']}({query_data['param']['key']}: ${query_data['param']['key']}, identifiers: $identifiers) {query_data['return']}
    }}
    """

    variables = {
        f"{query_data['param']['key']}": request_variables,
        "identifiers": {
            "accountIdentifier": account_id,
            "orgIdentifier": org_id,
            "projectIdentifier": project_id
        }
    }

    payload = {
        "query": query,
        "variables": variables
    }

    response = requests.post(chaos_uri, headers=headers, json=payload)
    try:
        response.raise_for_status()  # Raises HTTPError if the response status is 4xx/5xx
        json_response = response.json()
        if 'errors' in json_response:
            raise ValueError(f"GraphQL errors: {json_response['errors']}")
        return json_response
    except requests.exceptions.HTTPError as http_err:
        raise SystemError(f"HTTP error occurred: {http_err}")
    except Exception as err:
        raise SystemError(f"Other error occurred: {err}")


def register_infra(api_key, account_id, org_id, project_id, name, env_id, properties=None):
    """
    Registers infrastructure with the specified details using the Chaos API.

    :param api_key: The access token for authentication
    :param account_id: The account identifier
    :param org_id: The organization identifier
    :param project_id: The project identifier
    :param name: The name of the chaos infrastructure
    :param env_id: The environment identifier the chaos infrastructure will be enabled in
    :param properties: Optional dictionary of properties to configure the infrastructure. Defaults are used if not provided.
    :return: The response from the Chaos API as a JSON object
    """
    if properties is None:
        properties = {}
    
    # Set default values for properties if not provided
    default_properties = {
        "platformName": "Kubernetes",
        "infraNamespace": "hce",
        "serviceAccount": "hce",
        "infraScope": "namespace",
        "infraNsExists": True,
        "installationType": "MANIFEST",
        "isAutoUpgradeEnabled": False
    }

    # Update default properties with any provided properties
    request_variables = {**default_properties, **properties}
    request_variables["name"] = name
    request_variables["environmentID"] = env_id

    response = make_api_call(api_key, account_id, org_id, project_id, "register_infra", request_variables)

    # Extract the YAML manifest from the response
    manifest_yaml = response["data"]["registerInfra"]["manifest"]

    # Save the YAML manifest to a file
    file_name = f"/tmp/{name}_manifest.yaml"
    with open(file_name, "w") as file:
        file.write(manifest_yaml)

    return response


def add_probe(api_key, account_id, org_id, project_id, name, properties=None):
    """
    Adds a probe to the specified infrastructure using the Chaos API.

    :param api_key: The access token for authentication
    :param account_id: The account identifier
    :param org_id: The organization identifier
    :param project_id: The project identifier
    :param name: The name of the probe
    :param properties: Optional dictionary of properties to configure the probe. Defaults are used if not provided.
    :return: The response from the Chaos API as a JSON object
    """
    if properties is None:
        properties = {}
    
    hce_id = generate_hce_id(name)
    
    # Set default values for properties if not provided
    default_properties = {
        "probeTimeout": "10s",
        "interval": "5s",
        "retry": 3,
        "attempt": 3,
        "probePollingInterval": "1s",
        "initialDelay": "2s",
        "stopOnFailure": False,
        "url": "http://example.com",
        "method": {
            "get": {
                "criteria": "==",
                "responseCode": "200"
            }
        }
    }
    
    # Update default properties with any provided properties
    kubernetes_http_properties = {**default_properties, **properties}
    
    request_variables = {
        "name": name,
        "probeID": hce_id,
        "type": "httpProbe",
        "infrastructureType": "Kubernetes",
        "kubernetesHTTPProperties": kubernetes_http_properties
    }
    
    return make_api_call(api_key, account_id, org_id, project_id, "add_probe", request_variables)


def get_manifest_for_infra(api_key, account_id, org_id, project_id, name):
    """
    Creates a manifest file for the chaos infrastructure specified using the Chaos API.

    :param api_key: The access token for authentication
    :param account_id: The account identifier
    :param org_id: The organization identifier
    :param project_id: The project identifier
    :param name: The name of the chaos infrastructure
    """
    infra_id = None
    yaml_file = f"{name}-harness-chaos-enable.yml"
    chaos_infra = make_api_call(api_key, account_id, org_id, project_id, "list_infra")

    for infra in chaos_infra["data"]["listInfrasV2"]["infras"]:
        if infra["name"] == name:
            infra_id = infra["infraID"]
            break

    if infra_id:
        print(f"InfraID for '{name}': {infra_id}")
        chaos_manifest_raw = make_api_call(api_key, account_id, org_id, project_id, "get_infra_manifest", infra_id)
        with open(yaml_file, "wb") as file:
            file.write(chaos_manifest_raw["data"]["getInfraManifest"].encode('utf-8'))
        with open(yaml_file, "r") as file:
            validate_yaml_content(file)
    else:
        print(f"No infrastructure found with the name '{name}'")


#### KEYCLOAK FUNCTIONS ####
def generate_keycloak_token(keycloak_endpoint, keycloak_admin_user, keycloak_admin_pwd, cleanup=False):
    """
    Generates a Keycloak bearer token.

    :param keycloak_endpoint: The Keycloak endpoint.
    :param keycloak_admin_user: The Keycloak admin username.
    :param keycloak_admin_pwd: The Keycloak admin password.
    :param cleanup: Flag to continue the cleanup process on failure.
    :return: The Keycloak token if successful, otherwise None.
    """
    url = f"{keycloak_endpoint}/realms/master/protocol/openid-connect/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {
        "username": keycloak_admin_user,
        "password": keycloak_admin_pwd,
        "grant_type": "password",
        "client_id": "admin-cli"
    }

    response = requests.post(url, headers=headers, data=payload)
    
    if response.status_code != 200:
        print("Curl command failed.")
        if cleanup:
            print("Attempting to continue the cleanup process...")
        else:
            raise SystemExit(1)
    
    response_data = response.json()
    keycloak_token = response_data.get("access_token")

    if not keycloak_token:
        print("Token generation has failed. Response was:")
        print(response_data)
        if cleanup:
            print("Attempting to continue the cleanup process...")
        else:
            raise SystemExit(1)
    else:
        print("Token generation complete")
        return keycloak_token


def create_keycloak_user(keycloak_endpoint, keycloak_realm, keycloak_token, user_email, user_name, user_pwd):
    """
    Creates a user in Keycloak.

    :param keycloak_endpoint: The Keycloak endpoint.
    :param keycloak_realm: The Keycloak realm.
    :param keycloak_token: The Keycloak token.
    :param user_email: The email of the user to create.
    :param user_name: The name of the user to create.
    :param user_pwd: The password of the user to create.
    """
    url = f"{keycloak_endpoint}/admin/realms/{keycloak_realm}/users"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {keycloak_token}"
    }
    payload = {
        "email": user_email,
        "username": user_email,
        "firstName": user_name,
        "lastName": "Student",
        "emailVerified": True,
        "enabled": True,
        "requiredActions": [],
        "groups": [],
        "credentials": [
            {
                "type": "password",
                "value": user_pwd,
                "temporary": False
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload)
    response_code = response.status_code

    print(f"HTTP status code: {response_code}")

    if response_code != 201:
        print(f"The user creation API is not returning 201... this was the response: {response_code}")
        raise SystemExit(1)


def get_keycloak_user_id(keycloak_endpoint, keycloak_realm, keycloak_token, search_term):
    """
    Gets the Keycloak user ID based on the search term.

    :param keycloak_endpoint: The Keycloak endpoint.
    :param keycloak_realm: The Keycloak realm.
    :param keycloak_token: The Keycloak token.
    :param search_term: The term to search for the user.
    :return: The user ID if found, otherwise None.
    """
    url = f"{keycloak_endpoint}/admin/realms/{keycloak_realm}/users?briefRepresentation=true&first=0&max=11&search={search_term}"
    headers = {
        "Authorization": f"Bearer {keycloak_token}"
    }

    response = requests.get(url, headers=headers)
    response_data = response.json()
    user_id = response_data[0].get("id") if response_data else None

    print(f"Keycloak User ID: {user_id}")
    return user_id


def delete_keycloak_user(keycloak_endpoint, keycloak_realm, keycloak_token, user_email, cleanup=False):
    """
    Deletes a user from Keycloak based on their email.

    :param keycloak_endpoint: The Keycloak endpoint.
    :param keycloak_realm: The Keycloak realm.
    :param keycloak_token: The Keycloak token.
    :param user_email: The email of the user to delete.
    :param cleanup: Flag to continue the cleanup process on failure.
    """
    user_id = get_keycloak_user_id(keycloak_endpoint, keycloak_realm, keycloak_token, user_email)
    if not user_id:
        print("Failed to determine the User ID.")
    else:
        print(f"Deleting Keycloak User ID: {user_id}")
        url = f"{keycloak_endpoint}/admin/realms/{keycloak_realm}/users/{user_id}"
        headers = {
            "Authorization": f"Bearer {keycloak_token}"
        }

        response = requests.delete(url, headers=headers)
        response_code = response.status_code

        print(f"HTTP status code: {response_code}")

        if response_code != 204:
            print(f"The user deletion API is not returning 204... this was the response: {response_code}")
            if cleanup:
                print("Attempting to continue the cleanup process...")
            else:
                raise SystemExit(1)


#### INSTRUQT FUNCTIONS ####
def get_agent_variable(variable_name):
    """
    Retrieves the value of a specified variable using the 'agent variable get' command.

    :param variable_name: The name of the variable to retrieve.
    :return: The value of the specified variable as a string, or None if an error occurs.
    """
    try:
        result = subprocess.run(["agent", "variable", "get", variable_name], check=True, stdout=subprocess.PIPE, text=True)
        variable_value = result.stdout.strip()
        return variable_value
    except subprocess.CalledProcessError as e:
        print(f"Error retrieving {variable_name}: {e}")
        return None


def set_agent_variable(variable_name, variable_value):
    """
    Sets the value of a specified variable using the 'agent variable set' command.

    :param variable_name: The name of the variable to set.
    :param variable_value: The value of the variable to set.
    """
    try:
        subprocess.run(["agent", "variable", "set", variable_name, variable_value], check=True, stdout=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Error setting {variable_name}: {e}")


def raise_lab_failure_message(message_text):
    """
    Presents the user with a failure message after they've clicked the 'Check' button.

    :param message_text: The error/failure message to display to the workshop user.
    """
    subprocess.run(["fail-message", message_text], check=True)


#### K8S FUNCTIONS ####
def add_k8s_service_to_hosts(service_name, namespace, hostname):
    """
    Adds a Kubernetes service IP to the /etc/hosts file.

    :param service_name: The name of the Kubernetes service.
    :param namespace: The namespace of the Kubernetes service.
    :param hostname: The hostname to map to the service IP.
    """
    retries = 0
    max_retries = 5
    retry_delay = 10  # seconds

    print(f"Adding '{service_name}' to the hosts file.")
    while retries < max_retries:
        ip_address = subprocess.getoutput(f"kubectl get service {service_name} -n {namespace} -o=jsonpath='{{.status.loadBalancer.ingress[0].ip}}'")
        if ip_address and ip_address.lower() not in ["<none>", "none"]:
            print(f"Successfully retrieved IP address: {ip_address}")
            break
        retries += 1
        if retries == max_retries:
            print(f"Failed to retrieve IP for service {service_name} in namespace {namespace} after {max_retries} attempts.")
            return 1
        print(f"Retrying in {retry_delay} seconds... ({retries}/{max_retries})")
        time.sleep(retry_delay)

    # Update /etc/hosts
    with open("/etc/hosts", "r") as file:
        hosts_content = file.readlines()
    with open("/etc/hosts", "w") as file:
        for line in hosts_content:
            if hostname not in line:
                file.write(line)
        file.write(f"{ip_address} {hostname}\n")

    print(f"Added {hostname} with IP {ip_address} to /etc/hosts")


def get_k8s_loadbalancer_ip(service_name, namespace="default", max_attempts=15):
    """
    Retrieves the external IP of a Kubernetes LoadBalancer service.

    :param service_name: The name of the Kubernetes service.
    :param namespace: The namespace of the Kubernetes service. Default is 'default'.
    :param max_attempts: The maximum number of attempts to get the IP. Default is 15.
    :return: The external IP address of the LoadBalancer service.
    :raises SystemExit: If the IP address could not be retrieved within the maximum attempts.
    """
    print(f"Waiting for LoadBalancer IP for service {service_name}...")
    sleep_time = 5
    v1 = client.CoreV1Api()
    for attempt in range(1, max_attempts + 1):
        try:
            service = v1.read_namespaced_service(service_name, namespace)
            if service.status.load_balancer.ingress:
                external_ip = service.status.load_balancer.ingress[0].ip
                print(f"Attempt {attempt}/{max_attempts}:: Found IP {external_ip} for service {service_name}")
                return external_ip
            else:
                print(f"Attempt {attempt}/{max_attempts}:: No ingress IP found for service {service_name}. Retrying in {sleep_time} seconds...")
        except client.ApiException as e:
            print(f"Attempt {attempt}/{max_attempts}:: Failed to get service {service_name}. Error: {e}")
        time.sleep(sleep_time)
    print(f"Failed to get LoadBalancer IP for service {service_name} after {max_attempts} attempts.")
    raise SystemExit(1)


def render_manifest_from_template(template_file, output_path, apps_string):
    """
    Renders a Kubernetes manifest from a template by replacing placeholders with actual values.

    :param template_file: The path to the template file.
    :param output_path: The path where the rendered manifest will be saved.
    :param apps_string: A comma-separated string of app details in the format 'app_name:app_port:ip_address'.
    """
    def replace_values(template_file, output_file, app_name, app_port, ip_address):
        """
        Replaces placeholders in the template file with actual values and writes to the output file.

        :param template_file: The path to the template file.
        :param output_file: The path to the output file.
        :param app_name: The application name to replace in the template.
        :param app_port: The application port to replace in the template.
        :param ip_address: The IP address to replace in the template.
        """
        with open(template_file, "r") as file:
            content = file.read()
        content = content.replace("{{ APP_NAME }}", app_name)
        content = content.replace("{{ APP_PORT }}", app_port)
        content = content.replace("{{ HOSTNAME }}", os.getenv("HOST_NAME", ""))
        content = content.replace("{{ PARTICIPANT_ID }}", os.getenv("INSTRUQT_PARTICIPANT_ID", ""))
        content = content.replace("{{ IP_ADDRESS }}", ip_address)
        with open(output_file, "w") as file:
            file.write(content)

    apps = apps_string.split(",")
    for app in apps:
        print(f"Rendering template for {app}")
        app_name, app_port, ip_address = app.split(":")
        output_file = os.path.join(output_path, f"nginx-{app_name}.yaml")
        replace_values(template_file, output_file, app_name, app_port, ip_address)


def apply_k8s_manifests(manifests, namespace="default"):
    """
    Apply Kubernetes manifests.

    :param manifests: The path to the manifests file(s).
    :param namespace: The namespace for the Kubernetes secret. Default is 'default'.
    """
    k8s_client = client.ApiClient()
    for manifest in manifests:
        utils.create_from_yaml(k8s_client, manifest, namespace=namespace)


def wait_for_kubernetes_api(k8s_api):
    """
    Enables bash completion for kubectl.
    Waits for the Kubernetes API server to become available.

    :param k8s_api: The URL of the Kubernetes API server. (e.g., 'http://localhost:8001/api')
    """
    run_command('echo "source /usr/share/bash-completion/bash_completion" >> /root/.bashrc')
    run_command('echo "complete -F __start_kubectl k" >> /root/.bashrc')

    while True:
        try:
            response = requests.get(k8s_api)
            if response.status_code == 200:
                print("Kubernetes API server is available.")
                break
        except requests.RequestException:
            print("Waiting for the Kubernetes API server to become available...")
            time.sleep(2)


def create_k8s_secret(secret_name, secret_data, namespace="default"):
    """
    Create Kubernetes secret.

    :param secret_name: The name of the Kubernetes secret to create.
    :param namespace: The namespace for the Kubernetes secret. Default is 'default'.
    :raises SystemExit: If the secret could not be created.
    """
    print(f"Creating secret '{secret_name}'")

    v1 = client.CoreV1Api()
    secret = client.V1Secret(
        metadata=client.V1ObjectMeta(name=secret_name),
        string_data={"password": secret_data}
    )
    try:
        v1.create_namespaced_secret(namespace=namespace, body=secret)
    except client.ApiException as e:
        if e.status != 409:
            print(f"Exception when creating secret: {e}")
            raise SystemExit(1)


#### MISC FUNCTIONS ####
def setup_vs_code(service_port, code_server_directory):
    """
    Sets up VS Code server by downloading, installing, and configuring it.

    :param service_port: The port on which the VS Code server will run.
    :param code_server_directory: The directory where the VS Code server will store its files.
    """
    def download_and_install():
        """
        Downloads and installs VS Code server from the official repository.
        """
        url = "https://raw.githubusercontent.com/cdr/code-server/main/install.sh"
        response = requests.get(url)
        with open("/tmp/install.sh", "wb") as f:
            f.write(response.content)
        os.chmod("/tmp/install.sh", 0o755)
        subprocess.run(["bash", "/tmp/install.sh"], check=True)

    # Check if VS Code is already installed
    if subprocess.call(["which", "code-server"], stdout=subprocess.DEVNULL) == 0:
        print("VS Code already installed.")
    else:
        print("Installing VS Code...")
        download_and_install()

    # Setup VS Code
    os.makedirs("/home/harness/.local/share/code-server/User/", exist_ok=True)
    os.chown(
        "/home/harness/.local/share",
        pwd.getpwnam("harness").pw_uid,
        grp.getgrnam("harness").gr_gid
    )

    settings_url = "https://raw.githubusercontent.com/jtitra/field-workshops/main/assets/misc/vs_code/settings.json"
    settings_response = requests.get(settings_url)
    with open("/home/harness/.local/share/code-server/User/settings.json", "wb") as f:
        f.write(settings_response.content)

    service_url = "https://raw.githubusercontent.com/jtitra/field-workshops/main/assets/misc/vs_code/code-server.service"
    service_response = requests.get(service_url)
    with open("/etc/systemd/system/code-server.service", "wb") as f:
        f.write(service_response.content)

    # Update VS Code service
    with open("/etc/systemd/system/code-server.service", "r") as file:
        service_content = file.read()
    service_content = service_content.replace("EXAMPLEPORT", str(service_port))
    service_content = service_content.replace("EXAMPLEDIRECTORY", code_server_directory)

    create_systemd_service(service_content, "code-server")
    subprocess.run(["code-server", "--install-extension", "hashicorp.terraform"], check=True)


def generate_credentials_html(credentials):
    """
    Fetches the HTML template from a URL, populates it with credentials, and returns the generated HTML content.

    :param credentials: List of credentials to populate the template
    :return: Rendered HTML content as a string
    """
    template_url = "https://raw.githubusercontent.com/jtitra/field-workshops/main/assets/misc/credential_tab_template.html"
    try:
        # Fetch the HTML template from the URL
        response = requests.get(template_url)
        response.raise_for_status()
        html_template = response.text
        
        # Create a Jinja2 Template instance
        template = Template(html_template)
        
        # Render the template with the credentials data
        rendered_html = template.render(credentials=credentials)
        
        return rendered_html
    
    except requests.RequestException as e:
        print(f"Error fetching the template: {e}")
        return None


def create_systemd_service(service_content, service_name):
    """
    Creates a systemd service file and enables it to start on boot.

    :param service_content: The content to populate the .service file.
    :param service_name: The name of the service to create.
    """
    service_file_path = f"/etc/systemd/system/{service_name}.service"
    with open(service_file_path, "w") as service_file:
        service_file.write(service_content)

    # Reload systemd and enable the service
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", service_name], check=True)
    subprocess.run(["systemctl", "start", service_name], check=True)


def run_command(command):
    """
    Runs a shell command and prints success or failure message.

    :param command: The command to run.
    """
    try:
        subprocess.run(command, shell=True, check=True)
        print(f"Command '{command}' executed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to execute command '{command}'. Error: {e}")


def generate_random_suffix():
    """
    Generates a random suffix by hashing a random number and taking the first 10 characters.

    :return: A random suffix string of 10 characters.
    """
    random_number = random.randint(0, 32767)
    md5_hash = hashlib.md5(str(random_number).encode()).hexdigest()
    random_suffix = md5_hash[:10]
    return random_suffix


def generate_gke_credentials(generator_uri, user_name, output_file):
    """
    Generate GKE cluster credentials and output to file.

    :param generator_uri: The URL of the GKE Generator API server.
    :param user_name: The user to generate an env/namespace for.
    :param output_file: The file to create for the new kubeconfig yaml.
    """
    print("Getting GKE cluster credentials...")
    payload = json.dumps({"username": user_name})
    response = requests.post(
        f"{generator_uri}/create-user",
        headers={"Content-Type": "application/json"},
        data=payload,
        stream=True
    )
    with open(output_file, "wb") as f:
        f.write(response.content)
    print(f"HTTP status code: {response.status_code}")


def revoke_gke_credentials(generator_uri, user_name):
    """
    Revoke GKE cluster credentials.

    :param generator_uri: The URL of the GKE Generator API server.
    :param user_name: The user to revoke an env/namespace for.
    """
    print("Revoking GKE cluster credentials...")
    payload = json.dumps({"username": user_name})
    response = requests.post(
        f"{generator_uri}/delete-user",
        headers={"Content-Type": "application/json"},
        data=payload,
        stream=True
    )
    print(f"HTTP status code: {response.status_code}")


def validate_yaml_content(yaml_content):
    """
    Validates provided YAML data.

    :param yaml_content: The YAML data to validate.
    """
    try:
        yaml_data = list(yaml.safe_load_all(yaml_content))
        print("  INFO: Valid YAML provided.")
        return yaml_data
    except yaml.YAMLError as exc:
        print("  ERROR: The provided YAML is not valid.", exc)
        return None
