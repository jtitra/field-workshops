---
slug: lab3-detect-drift
id: caynop70jpgy
type: challenge
title: Lab 3 - Introduce Drift
teaser: Introduce and Detect Drift
notes:
- type: text
  contents: |
    This lab focuses on detecting configuration drifts in your infrastructure. Participants will learn how to set up drift detection, interpret its results, and understand the impact of drift on infrastructure management.
tabs:
- title: Harness Platform
  type: browser
  hostname: harness
- title: Shell
  type: terminal
  hostname: sandbox
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
</style><h2 class="cyan">Introduce Drift</h2>
<hr class="cyan">
<br>

## Now it's time to introduce some drift

### Switch to the ```>_Shell``` tab to continue

### List out our instances
```
aws ec2 describe-instances \
  --query "Reservations[*].Instances[*].[InstanceId,State.Name,InstanceType,Tags[?Key=='name'].Value | [0]]" \
  | jq
```

### Target one of them for some manual changes
```
TARGETED_INSTANCE="<replaceWithInstanceId>"
```

### Stop one of the EC2 instances we just provisioned
```
aws ec2 stop-instances \
  --instance-ids $TARGETED_INSTANCE \
  | jq
```

### Change that EC2 instance to ```t3.micro```
```
aws ec2 modify-instance-attribute \
  --instance-id $TARGETED_INSTANCE \
  --instance-type "{\"Value\": \"t3.micro\"}"
```

### Run the ```describe-instances``` command again to confirm the change

## Now let's create an IaCM Pipeline to detect drift
### Switch back to the ```Harness Platform``` to continue
Click on Pipelines in your left Nav <br>
And then click ```+Create Pipeline``` <br>
![Create_Pipeline.png](https://raw.githubusercontent.com/jtitra/field-workshops/main/se-workshop-iacm/assets/images/Create_Pipeline.png)


> **Create new Pipeline**
> - Name: ```IaCM Drift``` <br>
> - Store: ```Inline``` <br>

Click ```+Add Stage``` <br>
Choose **Infrastructure** stage type <br>
Give it a name: ```IaCM``` <br><br>

Keep the defaults on the **Infrastructure** tab and click **Next >** <br>
On the **Workspace** tab set the type to ```Runtime input``` and click **Next >** <br>
Select **Detect Drift** operation and click **Use Operation** <br>

Your pipeline should look like this: <br>
![IaCM_Drift.png](https://raw.githubusercontent.com/jtitra/field-workshops/main/se-workshop-iacm/assets/images/IaCM_Drift.png)
Click **Save** in the top right to save your new pipeline <br>

### Execute your new IaCM Pipeline
Now click **Run** and select your **Workspace** to execute the pipeline <br>
What do you expect to happen?<br><br><br>


Now that the piplne execution has completed, click on the ```Resources``` tab and see what drift has been detected.<br>

===============

Click the **Check** button to continue.
