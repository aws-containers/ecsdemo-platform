#!/usr/bin/env python3

# cdk: 1.41.0
from aws_cdk import (
    aws_ec2,
    aws_ecs,
    aws_iam,
    aws_ssm,
    aws_autoscaling,
    core,
    aws_appmesh,
    aws_ecs_patterns,
    aws_logs
)

from os import getenv


class BaseVPCStack(core.Stack):

    def __init__(self, scope: core.Stack, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # This resource alone will create a private/public subnet in each AZ as well as nat/internet gateway(s)
        self.vpc = aws_ec2.Vpc(
            self, "BaseVPC",
            cidr='10.0.0.0/24',
            
        )
        
        # Creating ECS Cluster in the VPC created above
        self.ecs_cluster = aws_ecs.Cluster(
            self, "ECSCluster",
            vpc=self.vpc,
            cluster_name="container-demo",
            container_insights=True
        )

        # Adding service discovery namespace to cluster
        self.ecs_cluster.add_default_cloud_map_namespace(
            name="service.local",
        )
        
        
        ###### CAPACITY PROVIDERS SECTION #####
        # Adding EC2 capacity to the ECS Cluster
        #self.asg = self.ecs_cluster.add_capacity(
        #    "ECSEC2Capacity",
        #    instance_type=aws_ec2.InstanceType(instance_type_identifier='t3.small'),
        #    min_capacity=0,
        #    max_capacity=10
        #)
        
        #core.CfnOutput(self, "EC2AutoScalingGroupName", value=self.asg.auto_scaling_group_name, export_name="EC2ASGName")
        ##### END CAPACITY PROVIDER SECTION #####

        ###### EC2 SPOT CAPACITY PROVIDER SECTION ######
        
        ## As of today, AWS CDK doesn't support Launch Templates on the AutoScaling construct, hence it
        ## doesn't support Mixed Instances Policy to combine instance types on Auto Scaling and adhere to Spot best practices
        ## In the meantime, CfnLaunchTemplate and CfnAutoScalingGroup resources are used to configure Spot capacity
        ## https://github.com/aws/aws-cdk/issues/6734
        
        #self.ecs_spot_instance_role = aws_iam.Role(
        #    self, "ECSSpotECSInstanceRole",
        #    assumed_by=aws_iam.ServicePrincipal("ec2.amazonaws.com"),
        #    managed_policies=[
        #        aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonEC2ContainerServiceforEC2Role"),
        #        aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonEC2RoleforSSM")
        #        ]
        #)
        #
        #self.ecs_spot_instance_profile = aws_iam.CfnInstanceProfile(
        #    self, "ECSSpotInstanceProfile",
        #    roles = [
        #            self.ecs_spot_instance_role.role_name
        #        ]
        #    )
        #
        ## This creates a Launch Template for the Auto Scaling group
        #self.lt = aws_ec2.CfnLaunchTemplate(
        #    self, "ECSEC2SpotCapacityLaunchTemplate",
        #    launch_template_data={
        #        "instanceType": "m5.large",
        #        "imageId": aws_ssm.StringParameter.value_for_string_parameter(
        #                    self,
        #                    "/aws/service/ecs/optimized-ami/amazon-linux-2/recommended/image_id"),
        #        "securityGroupIds": [ x.security_group_id for x in self.ecs_cluster.connections.security_groups ],
        #        "iamInstanceProfile": {"arn": self.ecs_spot_instance_profile.attr_arn},
        #        
        #        # Here we configure the ECS agent to drain Spot Instances upon catching a Spot Interruption notice from instance metadata
        #        "userData": core.Fn.base64(
        #            core.Fn.sub(
        #                "#!/usr/bin/bash\n"
        #                "echo ECS_CLUSTER=${cluster_name} >> /etc/ecs/ecs.config\n" 
        #                "sudo iptables --insert FORWARD 1 --in-interface docker+ --destination 169.254.169.254/32 --jump DROP\n"
        #                "sudo service iptables save\n"
        #                "echo ECS_ENABLE_SPOT_INSTANCE_DRAINING=true >> /etc/ecs/ecs.config\n" 
        #                "echo ECS_AWSVPC_BLOCK_IMDS=true >> /etc/ecs/ecs.config\n"  
        #                "cat /etc/ecs/ecs.config",
        #                variables = {
        #                    "cluster_name":self.ecs_cluster.cluster_name
        #                    }
        #                )
        #            )
        #        },
        #        launch_template_name="ECSEC2SpotCapacityLaunchTemplate")
        #        
        #self.ecs_ec2_spot_mig_asg = aws_autoscaling.CfnAutoScalingGroup(
        #    self, "ECSEC2SpotCapacity",
        #    min_size = "0",
        #    max_size = "10",
        #    vpc_zone_identifier = [ x.subnet_id for x in self.vpc.private_subnets ],
        #    mixed_instances_policy = {
        #        "instancesDistribution": {
        #            "onDemandAllocationStrategy": "prioritized",
        #            "onDemandBaseCapacity": 0,
        #            "onDemandPercentageAboveBaseCapacity": 0,
        #            "spotAllocationStrategy": "capacity-optimized"
        #            },
        #        "launchTemplate": {
        #            "launchTemplateSpecification": {
        #                "launchTemplateId": self.lt.ref,
        #                "version": self.lt.attr_default_version_number
        #            },
        #            "overrides": [
        #                {"instanceType": "m5.large"},
        #                {"instanceType": "m5d.large"},
        #                {"instanceType": "m5a.large"},
        #                {"instanceType": "m5ad.large"},
        #                {"instanceType": "m5n.large"},
        #                {"instanceType": "m5dn.large"},
        #                {"instanceType": "m3.large"},
        #                {"instanceType": "m4.large"},
        #                {"instanceType": "t3.large"},
        #                {"instanceType": "t2.large"}
        #            ]
        #        }
        #    }
        #)
        #
        #core.Tag.add(self.ecs_ec2_spot_mig_asg, "Name", self.ecs_ec2_spot_mig_asg.node.path) 
        #core.CfnOutput(self, "EC2SpotAutoScalingGroupName", value=self.ecs_ec2_spot_mig_asg.ref, export_name="EC2SpotASGName")       
        #
        ##### END EC2 SPOT CAPACITY PROVIDER SECTION #####
        
        # Namespace details as CFN output
        self.namespace_outputs = {
            'ARN': self.ecs_cluster.default_cloud_map_namespace.private_dns_namespace_arn,
            'NAME': self.ecs_cluster.default_cloud_map_namespace.private_dns_namespace_name,
            'ID': self.ecs_cluster.default_cloud_map_namespace.private_dns_namespace_id,
        }
        
        # Cluster Attributes
        self.cluster_outputs = {
            'NAME': self.ecs_cluster.cluster_name,
            'SECGRPS': str(self.ecs_cluster.connections.security_groups)
        }
        
        # When enabling EC2, we need the security groups "registered" to the cluster for imports in other service stacks
        if self.ecs_cluster.connections.security_groups:
            self.cluster_outputs['SECGRPS'] = str([x.security_group_id for x in self.ecs_cluster.connections.security_groups][0])
        
        # Frontend service to backend services on 3000
        self.services_3000_sec_group = aws_ec2.SecurityGroup(
            self, "FrontendToBackendSecurityGroup",
            allow_all_outbound=True,
            description="Security group for frontend service to talk to backend services",
            vpc=self.vpc
        )
        
        # Allow inbound 3000 from ALB to Frontend Service
        self.sec_grp_ingress_self_3000 = aws_ec2.CfnSecurityGroupIngress(
            self, "InboundSecGrp3000",
            ip_protocol='TCP',
            source_security_group_id=self.services_3000_sec_group.security_group_id,
            from_port=3000,
            to_port=3000,
            group_id=self.services_3000_sec_group.security_group_id
        )
        
        # Creating an EC2 bastion host to perform load test on private backend services
        amzn_linux = aws_ec2.MachineImage.latest_amazon_linux(
            generation=aws_ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
            edition=aws_ec2.AmazonLinuxEdition.STANDARD,
            virtualization=aws_ec2.AmazonLinuxVirt.HVM,
            storage=aws_ec2.AmazonLinuxStorage.GENERAL_PURPOSE
        )

        # Instance Role/profile that will be attached to the ec2 instance 
        # Enabling service role so the EC2 service can use ssm
        role = aws_iam.Role(self, "InstanceSSM", assumed_by=aws_iam.ServicePrincipal("ec2.amazonaws.com"))

        # Attaching the SSM policy to the role so we can use SSM to ssh into the ec2 instance
        role.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonEC2RoleforSSM"))

        # Reading user data, to install siege into the ec2 instance.
        with open("stresstool_user_data.sh") as f:
            user_data = f.read()

        # Instance creation
        self.instance = aws_ec2.Instance(self, "Instance",
            instance_name="{}-stresstool".format(stack_name),
            instance_type=aws_ec2.InstanceType("t3.medium"),
            machine_image=amzn_linux,
            vpc = self.vpc,
            role = role,
            user_data=aws_ec2.UserData.custom(user_data),
            security_group=self.services_3000_sec_group
                )
        
        # App Mesh Configuration
        # self.appmesh()
        
        # All Outputs required for other stacks to build
        core.CfnOutput(self, "NSArn", value=self.namespace_outputs['ARN'], export_name="NSARN")
        core.CfnOutput(self, "NSName", value=self.namespace_outputs['NAME'], export_name="NSNAME")
        core.CfnOutput(self, "NSId", value=self.namespace_outputs['ID'], export_name="NSID")
        core.CfnOutput(self, "FE2BESecGrp", value=self.services_3000_sec_group.security_group_id, export_name="SecGrpId")
        core.CfnOutput(self, "ECSClusterName", value=self.cluster_outputs['NAME'], export_name="ECSClusterName")
        core.CfnOutput(self, "ECSClusterSecGrp", value=self.cluster_outputs['SECGRPS'], export_name="ECSSecGrpList")
        core.CfnOutput(self, "ServicesSecGrp", value=self.services_3000_sec_group.security_group_id, export_name="ServicesSecGrp")
        core.CfnOutput(self, "StressToolEc2Id",value=self.instance.instance_id)
        core.CfnOutput(self, "StressToolEc2Ip",value=self.instance.instance_private_ip)
    
    
    
    # function to create app mesh
    def appmesh(self):
        
        # This will create the app mesh (control plane)
        self.mesh = aws_appmesh.Mesh(self,"EcsWorkShop-AppMesh", mesh_name="ecs-mesh")
        
        # We will create a App Mesh Virtual Gateway
        self.mesh_vgw = aws_appmesh.VirtualGateway(
            self,
            "Mesh-VGW",
            mesh=self.mesh,
            listeners=[aws_appmesh.VirtualGatewayListener.http(
                port=3000
                )],
            virtual_gateway_name="ecsworkshop-vgw"
        )
        
        # Creating the mesh gateway task for the frontend app
        # For more info related to App Mesh Proxy check https://docs.aws.amazon.com/app-mesh/latest/userguide/getting-started-ecs.html
        self.mesh_gw_proxy_task_def = aws_ecs.FargateTaskDefinition(
            self,
            "mesh-gw-proxy-taskdef",
            cpu=256,
            memory_limit_mib=512,
            family="mesh-gw-proxy-taskdef",
        )

        # LogGroup for the App Mesh Proxy Task
        self.logGroup = aws_logs.LogGroup(self,"ecsworkshopMeshGateway",
            #log_group_name="ecsworkshop-mesh-gateway",
            retention=aws_logs.RetentionDays.ONE_WEEK
        )
        
        # App Mesh Virtual Gateway Envoy proxy Task definition
        # For a use specific ECR region, please check https://docs.aws.amazon.com/app-mesh/latest/userguide/envoy.html
        container = self.mesh_gw_proxy_task_def.add_container(
            "mesh-gw-proxy-contdef",
            image=aws_ecs.ContainerImage.from_registry("public.ecr.aws/appmesh/aws-appmesh-envoy:v1.18.3.0-prod"),
            container_name="envoy",
            memory_reservation_mib=256,
            environment={
                "REGION": getenv('AWS_DEFAULT_REGION'),
                "ENVOY_LOG_LEVEL": "info",
                "ENABLE_ENVOY_STATS_TAGS": "1",
                # "ENABLE_ENVOY_XRAY_TRACING": "1",
                "APPMESH_RESOURCE_ARN": self.mesh_vgw.virtual_gateway_arn
            },
            essential=True,
            logging=aws_ecs.LogDriver.aws_logs(
                stream_prefix='/mesh-gateway',
                log_group=self.logGroup
            ),
            health_check=aws_ecs.HealthCheck(
                command=["CMD-SHELL","curl -s http://localhost:9901/server_info | grep state | grep -q LIVE"],
            )
        )
        
        # Default port where frontend app is listening
        container.add_port_mappings(
            aws_ecs.PortMapping(
                container_port=3000
            )
        )
        
        #ammmesh-xray-uncomment
        # xray_container = self.mesh_gw_proxy_task_def.add_container(
        #     "FrontendServiceXrayContdef",
        #     image=aws_ecs.ContainerImage.from_registry("amazon/aws-xray-daemon"),
        #     logging=aws_ecs.LogDriver.aws_logs(
        #         stream_prefix='/xray-container',
        #         log_group=self.logGroup
        #     ),
        #     essential=True,
        #     container_name="xray",
        #     memory_reservation_mib=256,
        #     user="1337"
        # )
        
        # container.add_container_dependencies(aws_ecs.ContainerDependency(
        #       container=xray_container,
        #       condition=aws_ecs.ContainerDependencyCondition.START
        #   )
        # )
        #ammmesh-xray-uncomment
        
        # For environment variables check https://docs.aws.amazon.com/app-mesh/latest/userguide/envoy-config.html
        self.mesh_gateway_proxy_fargate_service = aws_ecs_patterns.NetworkLoadBalancedFargateService(
            self,
            "MeshGW-Proxy-Fargate-Service",
            service_name='mesh-gw-proxy',
            cpu=256,
            memory_limit_mib=512,
            desired_count=1,
            listener_port=80,
            assign_public_ip=True,
            task_definition=self.mesh_gw_proxy_task_def,
            cluster=self.ecs_cluster,
            public_load_balancer=True,
            cloud_map_options=aws_ecs.CloudMapOptions(
                cloud_map_namespace=self.ecs_cluster.default_cloud_map_namespace,
                name='mesh-gw-proxy'
            )
        )
        
        # For testing purposes we will open any ipv4 requests to port 3000
        self.mesh_gateway_proxy_fargate_service.service.connections.allow_from_any_ipv4(
            port_range=aws_ec2.Port(protocol=aws_ec2.Protocol.TCP, string_representation="vtw_proxy", from_port=3000, to_port=3000),
            description="Allow NLB connections on port 3000"
        )
        
        self.mesh_gw_proxy_task_def.default_container.add_ulimits(aws_ecs.Ulimit(
            hard_limit=15000,
            name=aws_ecs.UlimitName.NOFILE,
            soft_limit=15000
            )
        )
        
        #Adding necessary policies for Envoy proxy to communicate with required services
        self.mesh_gw_proxy_task_def.execution_role.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryReadOnly"))
        self.mesh_gw_proxy_task_def.execution_role.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchLogsFullAccess"))
        
        self.mesh_gw_proxy_task_def.task_role.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchFullAccess"))
        # self.mesh_gw_proxy_task_def.task_role.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name("AWSXRayDaemonWriteAccess"))
        self.mesh_gw_proxy_task_def.task_role.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name("AWSAppMeshEnvoyAccess"))
        
        self.mesh_gw_proxy_task_def.execution_role.add_to_policy(
            aws_iam.PolicyStatement(
                actions=['ec2:DescribeSubnets'],
                resources=['*']
            )
        )
        
        core.CfnOutput(self, "MeshGwNlbDns",value=self.mesh_gateway_proxy_fargate_service.load_balancer.load_balancer_dns_name,export_name="MeshGwNlbDns")
        core.CfnOutput(self, "MeshArn",value=self.mesh.mesh_arn,export_name="MeshArn")
        core.CfnOutput(self, "MeshName",value=self.mesh.mesh_name,export_name="MeshName")
        core.CfnOutput(self, "MeshEnvoyServiceArn",value=self.mesh_gateway_proxy_fargate_service.service.service_arn,export_name="MeshEnvoyServiceArn")
        core.CfnOutput(self, "MeshVGWArn",value=self.mesh_vgw.virtual_gateway_arn,export_name="MeshVGWArn")
        core.CfnOutput(self, "MeshVGWName",value=self.mesh_vgw.virtual_gateway_name,export_name="MeshVGWName")
        
        


_env = core.Environment(account=getenv('AWS_ACCOUNT_ID'), region=getenv('AWS_DEFAULT_REGION'))
stack_name = "ecsworkshop-base"
app = core.App()
BaseVPCStack(app, stack_name, env=_env)
app.synth()
