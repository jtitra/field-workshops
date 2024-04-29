# File: instruqt_functions.sh
# Author: Joe Titra
# Version: 0.1.5
# Description: Common Functions used across the Instruqt SE Workshops

####################### BEGIN FUNCTION DEFINITION #######################
greet() { # Test function to print a greeting
  echo "Hello, $1!"
}

#### AWS ####
function is_valid_aws_account_id() { # Function to check if the input is a valid AWS account ID
    local account_id=$1

    echo "Validating AWS Account ID."
    [[ "$account_id" =~ ^[0-9]{12}$ ]]
}

function verify_aws_account_created() {
    local max_retries=10
    local retry_interval=10
    local retry_count=0

    echo "Verifying AWS Account has been created..."
    while true; do
        local aws_account_id=$(eval echo "\${INSTRUQT_AWS_ACCOUNT_${INSTRUQT_AWS_ACCOUNTS}_ACCOUNT_ID}")
        echo "    DEBUG: AWS Account ID: $aws_account_id"
        if is_valid_aws_account_id "$aws_account_id"; then
            echo "Valid AWS Account ID found: $aws_account_id"
            break
        else
            echo "Waiting for a valid AWS Account ID..."
            local retry_count=$((retry_count + 1))

            if [ "$retry_count" -ge "$max_retries" ]; then
                echo "Maximum retries reached without obtaining a valid AWS Account ID."
                exit 1
            fi
            sleep "$retry_interval"
        fi
    done
    echo "Proceeding with operations on AWS Account ID: $aws_account_id"
}

#### KEYCLOAK ####
function generate_keycloak_token() { # Function to generate bearer token
    local keycloak_endpoint="$1"
    local keycloak_admin_user="$2"
    local keycloak_admin_pwd="$3"

    echo "Generating Keycloak Token..."
    local response=$(curl --silent --request POST \
        --location "${keycloak_endpoint}/realms/master/protocol/openid-connect/token" \
        --header "Content-Type: application/x-www-form-urlencoded" \
        --data-urlencode "username=${keycloak_admin_user}" \
        --data-urlencode "password=${keycloak_admin_pwd}" \
        --data-urlencode "grant_type=password" \
        --data-urlencode "client_id=admin-cli")
  
    if [ $? -ne 0 ]; then
        echo "Curl command failed."
        if [ "$CLEANUP" = true ]; then
            echo "Attempting to continue the cleanup process..."
        else
            exit 1
        fi
    fi

    local keycloak_token=$(echo $response | jq -r ".access_token")

    if [ "$keycloak_token" == "null" ] || [ -z "$keycloak_token" ]; then
        echo "Token generation has failed. Response was:"
        echo "$response"
        if [ "$CLEANUP" = true ]; then
            echo "Attempting to continue the cleanup process..."
        else
            exit 1
        fi
    else
        echo "Token generation complete"
        KEYCLOAK_TOKEN="$keycloak_token"
    fi
}

function create_keycloak_user() { # Function to create workshop user
    local keycloak_endpoint="$1"
    local keycloak_realm="$2"
    local keycloak_token="$3"
    local user_email="$4"
    local user_name="$5"
    local user_pwd="$6"

    echo "Creating Keycloak User..."
    local response=$(curl --silent --request POST \
        --location "${keycloak_endpoint}/admin/realms/${keycloak_realm}/users" \
        --header "Content-Type: application/json" \
        --header "Authorization: Bearer ${keycloak_token}" \
        --write-out %{http_code} --output /dev/null \
        --data-raw '{
            "email": "'$user_email'",
            "username": "'$user_email'",
            "firstName": "'$user_name'",
            "lastName": "Student",
            "emailVerified": true,
            "enabled": true,
            "requiredActions": [],
            "groups": [],
            "credentials": [
                {
                    "type": "password",
                    "value": "'$user_pwd'",
                    "temporary": false
                }
            ]
        }')
  
    echo "HTTP status code: $response"
  
    if [[ "$response" -ne 201 ]] ; then
        echo "The user creation API is not returning 201... this was the response: $response"
        exit 1
    fi
}

function get_keycloak_user_id() { # Function to lookup workshop user id in Keycloak
    local keycloak_endpoint="$1"
    local keycloak_realm="$2"
    local keycloak_token="$3"
    local search_term="$4"

    echo "Getting Keycloak User ID..."
    local response=$(curl --silent --request GET \
        --location "${keycloak_endpoint}/admin/realms/${keycloak_realm}/users?briefRepresentation=true&first=0&max=11&search=${search_term}" \
        --header "Authorization: Bearer ${keycloak_token}")
  
    KEYCLOAK_USER_ID=$(echo $response | jq -r ".[0].id")
    echo "Keycloak User ID: $KEYCLOAK_USER_ID"
}

function delete_keycloak_user() { # Function to delete workshop user from Keycloak
    local keycloak_endpoint="$1"
    local keycloak_realm="$2"
    local keycloak_token="$3"
    local user_email="$4"

    # Get the workshop user ID from Keycloak
    get_keycloak_user_id $keycloak_endpoint $keycloak_realm $keycloak_token $user_email
    if [ "$KEYCLOAK_USER_ID" == "null" ]; then
        echo "Failed to determine the User ID."
    else
        echo "Deleting Keycloak User ID: $KEYCLOAK_USER_ID"
        local response=$(curl --silent --request DELETE \
            --location "${keycloak_endpoint}/admin/realms/${keycloak_realm}/users/${KEYCLOAK_USER_ID}" \
            --header "Authorization: Bearer ${keycloak_token}" \
            --write-out %{http_code} --output /dev/null)
      
        echo "HTTP status code: $response"
      
        if [[ "$response" -ne 204 ]] ; then
            echo "The user deletion API is not returning 204... this was the response: $response"
            if [ "$CLEANUP" = true ]; then
                echo "Attempting to continue the cleanup process..."
            else
                exit 1
            fi
        fi
    fi    
}

#### HARNESS ####
function create_harness_project() { # Function to create project in Harness
    local account_id="$1"
    local org_id="$2"
    local project_name="$3"
    local api_key="$4"

    echo "Creating Harness project '$project_name'..."
    local response=$(curl --silent --request POST \
        --location "https://app.harness.io/gateway/ng/api/projects?accountIdentifier=${account_id}&orgIdentifier=${org_id}" \
        --header "Content-Type: application/json" \
        --header "x-api-key: ${api_key}" \
        --data-raw '{
            "project":{
                "name":"'$project_name'",
                "orgIdentifier":"'$org_id'",
                "description":"Automated build via Instruqt.",
                "identifier":"'$project_name'",
                "tags":{
                    "automated": "yes",
                    "owner" : "instruqt"
                }
            }
        }')

    local create_status=$(echo $response | jq -r ".status")

    if [ "$create_status" == "SUCCESS" ]; then
        echo "Project '$project_name' created successfully."
    else
        echo "Failed to create project '$project_name'. Response: $response"
        exit 1
    fi
}

function invite_user_to_harness_project() { # Function to invite our new user to our new project
    local account_id="$1"
    local org_id="$2"
    local project_id="$3"
    local api_key="$4"
    local user_email="$5"
    #echo "Inviting the user to the project..."
    curl --silent --request POST \
        --location "https://app.harness.io/gateway/ng/api/user/users?accountIdentifier=${account_id}&orgIdentifier=${org_id}&projectIdentifier=${project_id}" \
        --header "Content-Type: application/json" \
        --header "x-api-key: ${api_key}" \
        --data-raw '{
            "emails":["'$user_email'"],
            "userGroups":["_project_all_users"],
            "roleBindings":[{
                "resourceGroupIdentifier":"_all_project_level_resources",
                "roleIdentifier":"_project_admin",
                "roleName":"Project Admin",
                "resourceGroupName":"All Project Level Resources",
                "managedRole":true
            }]
        }'
}

function invite_user_to_harness_project_loop() { # Function to handle inconsistent API calls
    local account_id="$1"
    local org_id="$2"
    local project_name="$3"
    local api_key="$4"
    local user_email="$5"
    local invite_attempts=0
    local max_attempts=4
    local invite_status=""

    echo "Inviting the user to the project..."
    local invite_response=$(invite_user_to_harness_project $account_id $org_id $project_name $api_key $user_email)
    local invite_status=$(echo $invite_response | jq -r ".status")
    echo "  DEBUG: Status: $invite_status"

    while [[ "$invite_status" != "SUCCESS" && $invite_attempts -lt $max_attempts ]]; do
        echo "User invite to project has failed. Retrying... Attempt: $((invite_attempts + 1))"
        local invite_response=$(invite_user_to_harness_project $account_id $org_id $project_name $api_key $user_email)
        local invite_status=$(echo $invite_response | jq -r ".status")
        echo "  DEBUG: Status: $invite_status"
        local invite_attempts=$((invite_attempts + 1))
        sleep 3
    done

    if [ "$invite_status" == "SUCCESS" ]; then
        echo "The API hit worked, your user was invited successfully."
    else
        echo "API hit to invite the user to the project has failed after $max_attempts attempts. Response: $invite_response"
        exit 1
    fi
}

function delete_harness_project() { # Function to delete project in Harness
    local account_id="$1"
    local org_id="$2"
    local project_name="$3"
    local api_key="$4"

    echo "Deleting Harness project '$project_name'..."
    local response=$(curl --silent --request DELETE \
        --location "https://app.harness.io/gateway/ng/api/projects/${project_name}?accountIdentifier=${account_id}&orgIdentifier=${org_id}" \
        --header "x-api-key: ${api_key}")

    local response_status=$(echo $response | jq -r ".status")

    if [ "$response_status" == "SUCCESS" ]; then
        echo "Project '$project_name' deleted successfully."
    else
        echo "Failed to delete project '$project_name'. Response: $response"
        if [ "$CLEANUP" = true ]; then
            echo "Attempting to continue the cleanup process..."
        else
            exit 1
        fi
    fi
}

function get_harness_user_id() { # Function to lookup workshop user id in Harness
    local account_id="$1"
    local org_id="$2"
    local project_id="$3"
    local api_key="$4"
    local search_term="$5"

    echo "Getting Harness User ID..."
    local response=$(curl -s \
        --location "https://app.harness.io/gateway/ng/api/user/aggregate?accountIdentifier=${account_id}&searchTerm=${search_term}" \
        --header "Content-Type: application/json" \
        --header "x-api-key: ${api_key}")

    HARNESS_USER_ID=$(echo $response | jq -r '.data.content[0].user.uuid')
    echo "Harness User ID: $HARNESS_USER_ID"
}

function delete_harness_user() { # Function to delete workshop user from Harness
    local account_id="$1"
    local org_id="$2"
    local project_id="$3"
    local api_key="$4"
    local user_email="$5"

     # Get the workshop user ID from Harness
    get_harness_user_id $account_id $org_id $project_id $api_key $user_email
    if [ "$HARNESS_USER_ID" == "null" ]; then
        echo "Failed to determine the User ID."
    else
        echo "Deleting Harness User ID: $HARNESS_USER_ID"
        local response=$(curl --silent --request DELETE \
            --location "https://app.harness.io/gateway/ng/api/user/$HARNESS_USER_ID?accountIdentifier=${account_id}" \
            --header "x-api-key: ${api_key}")
      
        local response_status=$(echo $response | jq -r ".status")

        if [ "$response_status" == "SUCCESS" ]; then
            echo "User deleted successfully."
        else
            echo "Failed to delete user. Response: $response"
            if [ "$CLEANUP" = true ]; then
                echo "Attempting to continue the cleanup process..."
            else
                exit 1
            fi
        fi
    fi    
}

######################## END FUNCTION DEFINITION ########################
