from aws_cdk import Duration, Stack
from constructs import Construct
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_rds as rds
import aws_cdk.aws_iam as iam
import aws_cdk.aws_dynamodb as dynamodb


class InfraStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        snapshot_arn: str = "arn:aws:rds:eu-west-1:559845934392:cluster-snapshot:replace",
        **kwargs
    ):
        super().__init__(scope, id, **kwargs)
        self.vpc = self._create_vpc()
        self.nat_instance = self._create_nat_instance()
        self.bastion, self.bastion_sg = self.create_bastion()
        self.sql_db, self.lambda_db_access_sg = self.create_postgres_database(
            self.vpc,
            self.bastion_sg,
            snapshot_id=snapshot_arn,
        )
        self.ddb = self.create_ddb_table()

    def create_bastion(self):
        # Create security group for bastion host
        bastion_sg = ec2.SecurityGroup(
            self,
            "BastionSG",
            vpc=self.vpc,
            description="Security group for bastion host",
            allow_all_outbound=True,
        )

        # Allow inbound SSH from home IP
        bastion_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4("37.228.196.240/32"),
            connection=ec2.Port.tcp(22),
            description="Allow SSH access from anywhere",
        )

        # Create IAM role for SSM
        ssm_role = iam.Role(
            self,
            "BastionSSMRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMManagedInstanceCore"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMFullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMManagedEC2InstanceDefaultPolicy"
                ),
            ],
        )

        # Create bastion host
        bastion = ec2.Instance(
            self,
            "BastionHost",
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T2, ec2.InstanceSize.MICRO
            ),
            machine_image=ec2.AmazonLinuxImage(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
            ),
            security_group=bastion_sg,
            key_name="nat_instances",  # Make sure this key pair exists in your AWS account
            role=ssm_role,  # Attach the SSM role to the bastion instance
        )

        return bastion, bastion_sg

    def create_ddb_table(self):
        ddb = dynamodb.Table(
            self,
            "navlogDB",
            partition_key=dynamodb.Attribute(
                name="id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            stream=dynamodb.StreamViewType.OLD_IMAGE,  # Enable DynamoDB Streams
        )
        ddb.add_global_secondary_index(
            partition_key=dynamodb.Attribute(
                name="type", type=dynamodb.AttributeType.STRING
            ),
            index_name="type-index",
        )
        return ddb

    def create_postgres_database(self, vpc, bastion, snapshot_id=None):
        sql_db_sg = ec2.SecurityGroup(self, "SQLDBSG", vpc=self.vpc)
        common_params = {
            "engine": rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_16_1
            ),
            "serverless_v2_max_capacity": 16,
            "serverless_v2_min_capacity": 0.5,
            "vpc": vpc,
            "writer": rds.ClusterInstance.serverless_v2(
                "writer", enable_performance_insights=True
            ),
            "security_groups": [sql_db_sg],
            "storage_encrypted": True,
            "monitoring_interval": Duration.seconds(60),
            "monitoring_role": iam.Role.from_role_arn(
                self,
                "monitoring-role",
                "arn:aws:iam::559845934392:role/emaccess",
            ),
            "cloudwatch_logs_exports": ["postgresql"],
        }

        if snapshot_id is not None:
            sql_db = rds.DatabaseClusterFromSnapshot(
                self, "dassie1", snapshot_identifier=snapshot_id, **common_params
            )
        else:
            sql_db = rds.DatabaseCluster(self, "dassie1", **common_params)

        # Allow the lambdas to access the database
        lambda_db_access_sg = ec2.SecurityGroup(self, "LambdaDBAccessSG", vpc=self.vpc)
        sql_db_sg.add_ingress_rule(lambda_db_access_sg, ec2.Port.tcp(5432))

        if bastion is not None:
            sql_db.connections.allow_default_port_from(bastion)
        return sql_db, lambda_db_access_sg

    def _create_nat_instance(self):
        # Create a NAT instance using Amazon Linux 2
        nat_instance = ec2.Instance(
            self,
            "NatInstance",
            instance_type=ec2.InstanceType(
                "t3.micro"
            ),  # Choose an appropriate instance type
            machine_image=ec2.MachineImage.latest_amazon_linux2(),  # Use Amazon Linux 2 AMI
            source_dest_check=False,
            vpc=self.vpc,
            vpc_subnets={
                "subnet_type": ec2.SubnetType.PUBLIC
            },  # Place in a public subnet
            key_pair=ec2.KeyPair.from_key_pair_name(
                self, "NatInstanceKeyPair", "nat_instances"
            ),
            user_data=ec2.UserData.custom(
                """#!/bin/bash
                # Update the system
                yum update -y
                # Install iptables if not already installed
                yum install -y iptables-services
                systemctl enable iptables
                systemctl start iptables
                # Enable IP forwarding
                echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.d/custom-ip-forwarding.conf
                sysctl -p /etc/sysctl.d/custom-ip-forwarding.conf


                /sbin/iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
                /sbin/iptables -F FORWARD
                service iptables save
                systemctl restart iptables
                """
            ),
        )

        # Allow the NAT instance to access the internet
        nat_instance_sg = ec2.SecurityGroup(
            self,
            "NatInstanceSG",
            vpc=self.vpc,
            allow_all_outbound=True,
        )

        # Update route tables to use the NAT instance
        for subnet in self.vpc.private_subnets:
            subnet.add_route(
                "NatRoute",
                router_id=nat_instance.instance_id,
                router_type=ec2.RouterType.INSTANCE,
                destination_cidr_block="0.0.0.0/0",
            )
            nat_instance_sg.add_ingress_rule(
                peer=ec2.Peer.ipv4(
                    subnet.ipv4_cidr_block
                ),  # Use ipv4_cidr_block for the peer
                connection=ec2.Port.all_traffic(),
            )
        nat_instance.add_security_group(nat_instance_sg)
        return nat_instance

    def _create_vpc(self):
        # Create the VPC with both public and private subnets
        vpc = ec2.Vpc(
            self,
            "AuroraVpc1",
            max_azs=2,  # Maximum Availability Zones
            nat_gateways=0,  # Disable NAT gateways
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=18,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=18,
                ),
            ],
        )
        ec2.GatewayVpcEndpoint(
            self,
            "S3VpcEndpoint",
            vpc=vpc,
            service=ec2.GatewayVpcEndpointAwsService.S3,
        )
        ec2.GatewayVpcEndpoint(
            self,
            "DynamoDBVpcEndpoint",
            vpc=vpc,
            service=ec2.GatewayVpcEndpointAwsService.DYNAMODB,
        )
        return vpc
