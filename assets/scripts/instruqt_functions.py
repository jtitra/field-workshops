# File: instruqt_functions.py
# Author: Joe Titra
# Version: 0.1.0
# Description: Common Functions used across the Instruqt SE Workshops
# History:
#   Version    |    Author    |    Date    |  Comments
#   v0.1.0     | Joe Titra    | 06/21/2024 | Intial version migrating from bash

#### IMPORTS ####
import os
import pwd
import grp
import subprocess
import time
import requests
from jinja2 import Template
import json
####################### BEGIN FUNCTION DEFINITION #######################

def verify_harness_login(api_key, account_id, user_name):
    """
    Verifies the login of a user in Harness by checking the audit logs.

    :param api_key: The API key for accessing Harness API.
    :param account_id: The account ID in Harness.
    :param user_name: The user name to verify the login for.
    """
    time_filter = int(time.time() * 1000) - 300000  # Current time in milliseconds minus 5 minutes

    print(f"Validating Harness login for user '{user_name}'...")
    url = f"https://app.harness.io/gateway/audit/api/audits/list?accountIdentifier={account_id}"
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
    else:
        print("No Logins were found in the last 5 minutes")
        subprocess.run(
            ["fail-message", "No Login events were found for your user via the Harness API."],
            check=True)

#### MISC ####
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

def get_k8s_loadbalancer_ip(service_name, namespace="", max_attempts=30, sleep_time=2):
    """
    Retrieves the external IP of a Kubernetes LoadBalancer service.

    :param service_name: The name of the Kubernetes service.
    :param namespace: The namespace of the Kubernetes service. Defaults to the current namespace.
    :param max_attempts: The maximum number of attempts to retrieve the IP. Defaults to 30.
    :param sleep_time: The time to wait between attempts in seconds. Defaults to 2 seconds.
    :return: The external IP address of the LoadBalancer service.
    :raises SystemExit: If the IP address could not be retrieved within the maximum attempts.
    """
    print(f"Waiting for LoadBalancer IP for service {service_name}...")
    for attempt in range(1, max_attempts + 1):
        cmd = f"kubectl get svc {service_name}"
        if namespace:
            cmd += f" -n {namespace}"
        cmd += " -o jsonpath='{.status.loadBalancer.ingress[0].ip}'"
        external_ip = subprocess.getoutput(cmd)
        if external_ip:
            print(f"Service {service_name} has an external IP: {external_ip}")
            return external_ip
        print(f"Attempt {attempt}/{max_attempts}: LoadBalancer IP not yet available, retrying in {sleep_time}s...")
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

def create_systemd_service(service_content, service_name):
    """
    Creates a systemd service file and enables it to start on boot.

    :param service_content: The content to populate the .service file.
    :param service_name: The name of the service to create.
    """

    service_file_path = "/etc/systemd/system/{service_name}.service"
    with open(service_file_path, "w") as service_file:
        service_file.write(service_content)

    # Reload systemd and enable the service
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", service_name], check=True)
    subprocess.run(["systemctl", "start", service_name], check=True)

######################## END FUNCTION DEFINITION ########################
