from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from google.cloud import storage, bigquery, pubsub_v1, monitoring_v3
from google.cloud.monitoring_v3 import AlertPolicy
from google.cloud import aiplatform
from google.cloud import compute_v1
from google.cloud import container_v1
from google.cloud.container_v1 import Cluster
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GCPConfig(BaseModel):
    """Configuration for GCP services"""
    project_id: str = Field(..., description="GCP project ID")
    region: str = Field(default="us-central1", description="Default GCP region")
    zone: str = Field(default="us-central1-a", description="Default GCP zone")
    credentials_path: Optional[str] = Field(default=None, description="Path to service account credentials")

class StorageConfig(BaseModel):
    """Configuration for GCP Storage"""
    bucket_name: str
    location: Optional[str] = None
    storage_class: str = "STANDARD"
    versioning_enabled: bool = False

class BigQueryConfig(BaseModel):
    """Configuration for BigQuery"""
    dataset_id: str
    location: Optional[str] = None
    table_id: Optional[str] = None
    schema: Optional[List[Dict[str, Any]]] = None

class GKEConfig(BaseModel):
    """Configuration for Google Kubernetes Engine"""
    cluster_name: str
    node_count: int = 3
    machine_type: str = "e2-medium"
    disk_size_gb: int = 100
    auto_scaling: bool = True
    min_nodes: Optional[int] = None
    max_nodes: Optional[int] = None

class GCPTool:
    """Tool for managing GCP resources and services"""
    
    def __init__(self, config: GCPConfig):
        self.config = config
        self.storage_client = storage.Client(project=config.project_id)
        self.bq_client = bigquery.Client(project=config.project_id)
        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()
        self.monitoring_client = monitoring_v3.AlertPolicyServiceClient()
        self.compute_client = compute_v1.InstancesClient()
        self.container_client = container_v1.ClusterManagerClient()
        
    # Storage Operations
    def create_bucket(self, config: StorageConfig) -> storage.Bucket:
        """Create a new GCS bucket"""
        try:
            bucket = self.storage_client.bucket(config.bucket_name)
            bucket.storage_class = config.storage_class
            bucket.location = config.location or self.config.region
            bucket = self.storage_client.create_bucket(bucket)
            
            if config.versioning_enabled:
                bucket.versioning_enabled = True
                bucket.patch()
                
            return bucket
        except Exception as e:
            logger.error(f"Error creating bucket: {str(e)}")
            raise
            
    def upload_file(self, bucket_name: str, source_file: str, destination_blob: str) -> storage.Blob:
        """Upload a file to GCS"""
        try:
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(destination_blob)
            blob.upload_from_filename(source_file)
            return blob
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise
            
    # BigQuery Operations
    def create_dataset(self, config: BigQueryConfig) -> bigquery.Dataset:
        """Create a new BigQuery dataset"""
        try:
            dataset = bigquery.Dataset(f"{self.config.project_id}.{config.dataset_id}")
            dataset.location = config.location or self.config.region
            return self.bq_client.create_dataset(dataset)
        except Exception as e:
            logger.error(f"Error creating dataset: {str(e)}")
            raise
            
    def create_table(self, config: BigQueryConfig) -> bigquery.Table:
        """Create a new BigQuery table"""
        try:
            dataset_ref = self.bq_client.dataset(config.dataset_id)
            table_ref = dataset_ref.table(config.table_id)
            table = bigquery.Table(table_ref, schema=config.schema)
            return self.bq_client.create_table(table)
        except Exception as e:
            logger.error(f"Error creating table: {str(e)}")
            raise
            
    def query(self, query: str) -> bigquery.job.QueryJob:
        """Execute a BigQuery query"""
        try:
            return self.bq_client.query(query)
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            raise
            
    # Pub/Sub Operations
    def create_topic(self, topic_name: str) -> str:
        """Create a new Pub/Sub topic"""
        try:
            topic_path = self.publisher.topic_path(self.config.project_id, topic_name)
            return self.publisher.create_topic(request={"name": topic_path})
        except Exception as e:
            logger.error(f"Error creating topic: {str(e)}")
            raise
            
    def create_subscription(self, topic_name: str, subscription_name: str) -> str:
        """Create a new Pub/Sub subscription"""
        try:
            topic_path = self.publisher.topic_path(self.config.project_id, topic_name)
            subscription_path = self.subscriber.subscription_path(
                self.config.project_id, subscription_name
            )
            return self.subscriber.create_subscription(
                request={"name": subscription_path, "topic": topic_path}
            )
        except Exception as e:
            logger.error(f"Error creating subscription: {str(e)}")
            raise
            
    # Monitoring Operations
    def create_alert_policy(self, display_name: str, filter_str: str,
                          threshold_value: float) -> AlertPolicy:
        """Create a new monitoring alert policy"""
        try:
            project_name = f"projects/{self.config.project_id}"
            
            condition = monitoring_v3.AlertPolicy.Condition(
                display_name=f"{display_name} condition",
                condition_threshold=monitoring_v3.AlertPolicy.Condition.MetricThreshold(
                    filter=filter_str,
                    comparison=monitoring_v3.ComparisonType.COMPARISON_GT,
                    threshold_value=threshold_value
                )
            )
            
            alert_policy = monitoring_v3.AlertPolicy(
                display_name=display_name,
                conditions=[condition],
                combiner=monitoring_v3.AlertPolicy.ConditionCombinerType.AND
            )
            
            return self.monitoring_client.create_alert_policy(
                request={"name": project_name, "alert_policy": alert_policy}
            )
        except Exception as e:
            logger.error(f"Error creating alert policy: {str(e)}")
            raise
            
    # Compute Engine Operations
    def create_instance(self, instance_name: str, machine_type: str = "n1-standard-1",
                       source_image: str = "debian-cloud/debian-10") -> compute_v1.Instance:
        """Create a new Compute Engine instance"""
        try:
            instance = compute_v1.Instance()
            instance.name = instance_name
            instance.machine_type = f"zones/{self.config.zone}/machineTypes/{machine_type}"
            
            disk = compute_v1.AttachedDisk()
            disk.initialize_params.source_image = f"projects/{source_image}"
            disk.boot = True
            instance.disks = [disk]
            
            network_interface = compute_v1.NetworkInterface()
            network_interface.network = "global/networks/default"
            instance.network_interfaces = [network_interface]
            
            return self.compute_client.insert(
                project=self.config.project_id,
                zone=self.config.zone,
                instance_resource=instance
            )
        except Exception as e:
            logger.error(f"Error creating instance: {str(e)}")
            raise
            
    # GKE Operations
    def create_cluster(self, config: GKEConfig) -> Cluster:
        """Create a new GKE cluster"""
        try:
            parent = f"projects/{self.config.project_id}/locations/{self.config.zone}"
            
            cluster = {
                "name": config.cluster_name,
                "initial_node_count": config.node_count,
                "node_config": {
                    "machine_type": config.machine_type,
                    "disk_size_gb": config.disk_size_gb,
                }
            }
            
            if config.auto_scaling:
                cluster["autoscaling"] = {
                    "enabled": True,
                    "min_node_count": config.min_nodes or 1,
                    "max_node_count": config.max_nodes or 5
                }
                
            request = {"parent": parent, "cluster": cluster}
            operation = self.container_client.create_cluster(request)
            return operation.result()
        except Exception as e:
            logger.error(f"Error creating cluster: {str(e)}")
            raise
            
    # AI Platform Operations
    def create_dataset(self, display_name: str, metadata_schema_uri: str) -> aiplatform.Dataset:
        """Create a new Vertex AI dataset"""
        try:
            return aiplatform.Dataset.create(
                display_name=display_name,
                metadata_schema_uri=metadata_schema_uri,
                project=self.config.project_id,
                location=self.config.region
            )
        except Exception as e:
            logger.error(f"Error creating dataset: {str(e)}")
            raise
            
    def train_model(self, display_name: str, dataset: aiplatform.Dataset,
                   training_args: Dict[str, Any]) -> aiplatform.Model:
        """Train a new model on Vertex AI"""
        try:
            job = aiplatform.CustomTrainingJob(
                display_name=display_name,
                project=self.config.project_id,
                location=self.config.region
            )
            
            model = job.run(
                dataset=dataset,
                model_display_name=f"{display_name}-model",
                **training_args
            )
            
            return model
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            raise
            
    def deploy_model(self, model: aiplatform.Model, machine_type: str = "n1-standard-4",
                    min_replicas: int = 1) -> aiplatform.Endpoint:
        """Deploy a model to an endpoint"""
        try:
            endpoint = model.deploy(
                machine_type=machine_type,
                min_replica_count=min_replicas,
                project=self.config.project_id,
                location=self.config.region
            )
            return endpoint
        except Exception as e:
            logger.error(f"Error deploying model: {str(e)}")
            raise 