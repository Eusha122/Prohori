"""Create (or reuse) Prohori's AWS server in Mumbai. Safe to run again: existing pieces are reused.

Creates:
  - IAM role + instance profile "prohori-web-role": lets the server call Amazon Nova on Bedrock only
    (no AWS keys are ever copied to the server)
  - security group "prohori-web-sg": web (80/443) open to all, SSH (22) only from this computer's IP
  - SSH key pair "prohori-mumbai" (private key saved to ~/.ssh/prohori-mumbai.pem, never in the repo)
  - EC2 t3.small, Ubuntu 24.04, 30 GB disk, IMDSv2, with a fixed Elastic IP
Writes deploy/state.json (instance id, IP) - git-ignored.
Run with the local .env keys:  .venv\\Scripts\\python deploy\\aws_setup.py
"""
import json
import os
import time
import urllib.request
from pathlib import Path

import boto3
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
REGION = "ap-south-1"
NAME = "prohori-web"
ROLE = "prohori-web-role"
SG = "prohori-web-sg"
KEY = "prohori-mumbai"
KEY_FILE = Path.home() / ".ssh" / f"{KEY}.pem"
STATE = ROOT / "deploy" / "state.json"

ec2 = boto3.client("ec2", region_name=REGION)
iam = boto3.client("iam")
account = boto3.client("sts").get_caller_identity()["Account"]


def role():
    trust = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"},
                                                      "Action": "sts:AssumeRole"}]}
    try:
        iam.create_role(RoleName=ROLE, AssumeRolePolicyDocument=json.dumps(trust),
                        Description="Prohori web server: call Amazon Nova on Bedrock")
        print("created role", ROLE)
    except iam.exceptions.EntityAlreadyExistsException:
        print("role exists", ROLE)
    policy = {"Version": "2012-10-17", "Statement": [{
        "Sid": "NovaOnly", "Effect": "Allow",
        "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
        "Resource": ["arn:aws:bedrock:*::foundation-model/amazon.nova-*",
                     f"arn:aws:bedrock:*:{account}:inference-profile/us.amazon.nova-*"]}]}
    iam.put_role_policy(RoleName=ROLE, PolicyName="nova-only", PolicyDocument=json.dumps(policy))
    try:
        iam.create_instance_profile(InstanceProfileName=ROLE)
        iam.add_role_to_instance_profile(InstanceProfileName=ROLE, RoleName=ROLE)
        print("created instance profile; waiting for IAM to spread")
        time.sleep(15)
    except iam.exceptions.EntityAlreadyExistsException:
        pass


def security_group():
    my_ip = urllib.request.urlopen("https://checkip.amazonaws.com", timeout=10).read().decode().strip()
    vpc = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])["Vpcs"][0]["VpcId"]
    found = ec2.describe_security_groups(Filters=[{"Name": "group-name", "Values": [SG]}, {"Name": "vpc-id", "Values": [vpc]}])["SecurityGroups"]
    if found:
        sg = found[0]["GroupId"]
        print("security group exists", sg)
    else:
        sg = ec2.create_security_group(GroupName=SG, Description="Prohori web: HTTP/HTTPS public, SSH admin only",
                                       VpcId=vpc)["GroupId"]
        print("created security group", sg)
    rules = [
        {"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80, "IpRanges": [{"CidrIp": "0.0.0.0/0"}], "Ipv6Ranges": [{"CidrIpv6": "::/0"}]},
        {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "IpRanges": [{"CidrIp": "0.0.0.0/0"}], "Ipv6Ranges": [{"CidrIpv6": "::/0"}]},
        {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": f"{my_ip}/32", "Description": "admin"}]},
    ]
    for r in rules:
        try:
            ec2.authorize_security_group_ingress(GroupId=sg, IpPermissions=[r])
        except ec2.exceptions.ClientError as e:
            if "InvalidPermission.Duplicate" not in str(e):
                raise
    print("SSH allowed only from", my_ip)
    return sg


def key_pair():
    names = [k["KeyName"] for k in ec2.describe_key_pairs()["KeyPairs"]]
    if KEY in names and KEY_FILE.exists():
        print("key pair exists")
        return
    if KEY in names:
        ec2.delete_key_pair(KeyName=KEY)
    k = ec2.create_key_pair(KeyName=KEY, KeyType="ed25519")
    KEY_FILE.parent.mkdir(exist_ok=True)
    KEY_FILE.write_text(k["KeyMaterial"])
    os.chmod(KEY_FILE, 0o600)
    print("saved SSH key to", KEY_FILE)


USER_DATA = """#!/bin/bash
set -e
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv python3-pip nodejs npm caddy sqlite3 unzip
timedatectl set-timezone Asia/Dhaka
mkdir -p /opt/prohori && chown ubuntu:ubuntu /opt/prohori
touch /var/lib/cloud/instance/prohori-base-ready
"""


def instance(sg):
    found = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": [NAME]},
                                            {"Name": "instance-state-name", "Values": ["pending", "running", "stopped"]}])
    found = [i for r in found["Reservations"] for i in r["Instances"]]
    if found:
        iid = found[0]["InstanceId"]
        print("instance exists", iid)
        return iid
    imgs = ec2.describe_images(Owners=["099720109477"], Filters=[
        {"Name": "name", "Values": ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]},
        {"Name": "state", "Values": ["available"]}])["Images"]
    ami = max(imgs, key=lambda i: i["CreationDate"])["ImageId"]
    r = ec2.run_instances(
        ImageId=ami, InstanceType="t3.small", MinCount=1, MaxCount=1, KeyName=KEY, SecurityGroupIds=[sg],
        IamInstanceProfile={"Name": ROLE}, UserData=USER_DATA,
        BlockDeviceMappings=[{"DeviceName": "/dev/sda1", "Ebs": {"VolumeSize": 30, "VolumeType": "gp3", "DeleteOnTermination": True}}],
        MetadataOptions={"HttpTokens": "required", "HttpEndpoint": "enabled", "HttpPutResponseHopLimit": 2},
        TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": NAME}, {"Key": "project", "Value": "prohori"}]},
                           {"ResourceType": "volume", "Tags": [{"Key": "Name", "Value": NAME}, {"Key": "project", "Value": "prohori"}]}])
    iid = r["Instances"][0]["InstanceId"]
    print("launched", iid, "from", ami)
    return iid


def elastic_ip(iid):
    ec2.get_waiter("instance_running").wait(InstanceIds=[iid])
    addrs = ec2.describe_addresses(Filters=[{"Name": "tag:Name", "Values": [NAME]}])["Addresses"]
    if addrs:
        alloc = addrs[0]["AllocationId"]
        ip = addrs[0]["PublicIp"]
    else:
        a = ec2.allocate_address(Domain="vpc", TagSpecifications=[{"ResourceType": "elastic-ip", "Tags": [{"Key": "Name", "Value": NAME}]}])
        alloc, ip = a["AllocationId"], a["PublicIp"]
        print("allocated Elastic IP", ip)
    ec2.associate_address(InstanceId=iid, AllocationId=alloc, AllowReassociation=True)
    return ip


if __name__ == "__main__":
    role()
    sg = security_group()
    key_pair()
    iid = instance(sg)
    ip = elastic_ip(iid)
    STATE.write_text(json.dumps({"region": REGION, "instance_id": iid, "ip": ip, "key_file": str(KEY_FILE)}, indent=2))
    print(f"\nREADY: instance {iid} at {ip}")
