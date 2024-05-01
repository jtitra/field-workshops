---
slug: lab1-creating-a-workspace
id: cacladdx8lkl
type: challenge
title: Lab 1 - Creating a Workspace
teaser: Setting up your first IaCM Workspace
notes:
- type: text
  contents: |
    In this lab, participants will learn how to create and configure a workspace in Harness IaCM. This will serve as the foundation for the subsequent labs, where you will manage your infrastructure as code.
tabs:
- title: Harness Platform
  type: browser
  hostname: harness
- title: Lab Credentials
  type: service
  hostname: sandbox
  path: /aws_credentials.html
  port: 8000
difficulty: basic
timelimit: 1600
---

<style type="text/css" rel="stylesheet">
hr.cyan { background-color: cyan; color: cyan; height: 2px; margin-bottom: -10px; }
h2.cyan { color: cyan; }
</style><h2 class="cyan">Create an IaCM Workspace</h2>
<hr class="cyan">
<br>

## Now it's time to create an IaCM Workspace
![IaCM_Module.png](https://raw.githubusercontent.com/jtitra/field-workshops/main/se-workshop-iacm/assets/images/IaCM_Module.png)

Select the **Infrastructure as Code Management** module from the list <br>

Click on **Workspaces** in the left Nav <br>
And then click ```+New Workspace``` <br>
![New_Workspace.png](https://raw.githubusercontent.com/jtitra/field-workshops/main/se-workshop-iacm/assets/images/New_Workspace.png)


> **New Workspace**
> - Name: ```demo-workspace``` <br>
> - Cloud Cost Estimation: ```ON``` <br>
> - **Provisioner** <br>
> -- Connector: ```instruqt-workshop-connector``` <br>
> -- Type: ```Terraform``` <br>
> -- Version: ```1.5.6``` <br>
> - **Repository** <br>
> -- Connector: ```demo-github``` <br>
> -- Repository: ```jtitra/iacm-workshop``` <br>
> -- Git Fetch Type: ```Latest from Branch``` <br>
> -- Branch: ```main``` <br>
> -- File Path: ```aws/v1``` <br>

Click **Save**

### Configure Workspace
Click on the **Variables** tab <br>
Add two ```Environment Variables``` <br>

| Key           | Value     |
|---------------|-----------|
| **AWS_ACCESS_KEY_ID**     | [[ Instruqt-Var key="AWS_ACCESS_KEY_ID" hostname="sandbox" ]]     |
| **AWS_SECRET_ACCESS_KEY** | [[ Instruqt-Var key="AWS_SECRET_ACCESS_KEY" hostname="sandbox" ]] |

*You could also use the preconfigured **secret**: ```aws-secret``` or create your own instead of storing the sensitive **AWS_SECRET_ACCESS_KEY** in plain-text*

Add three Terraform Variables <br>

| Key           | Value     |
|---------------|-----------|
| **instance_type** | `t2.micro` |
| **extra**         | `test`     |
| **bucket_name**   | `bucket1`  |


*You could also reference a variable file from another location or another repository entirely. By default, it looks for the ```variables.tf``` that is defined in Workspaces > Repo > File Path.*

===============

Click the **Check** button to continue.
