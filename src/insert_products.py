"""Module for inserting product JSON documents into Azure Cosmos DB."""

import json
import os
from typing import List, Dict, Any
from azure.cosmos import CosmosClient, PartitionKey
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential, ClientSecretCredential

# Load environment variables
load_dotenv()

class CosmosDBProductInserter:
    """Handles insertion of product data into Azure Cosmos DB."""
    
    def __init__(self):
        """Initialize the Cosmos DB client and database/container references."""
        # Get connection details from environment variables
        self.endpoint = os.getenv('COSMOS_ENDPOINT')
        self.key = os.getenv('COSMOS_KEY')
        self.database_name = os.getenv('COSMOS_DATABASE', 'products-db')
        self.container_name = os.getenv('COSMOS_CONTAINER', 'products')
        
        # Service principal credentials
        self.client_id = os.getenv('AZURE_CLIENT_ID')
        self.client_secret = os.getenv('AZURE_CLIENT_SECRET')
        self.tenant_id = os.getenv('AZURE_TENANT_ID')
        
        if not self.endpoint:
            raise ValueError("COSMOS_ENDPOINT environment variable is required")
        
        # Initialize Cosmos DB client with authentication
        if self.key:
            # Use key-based authentication
            self.client = CosmosClient(self.endpoint, self.key)
        elif self.client_id and self.client_secret and self.tenant_id:
            # Use service principal authentication
            try:
                credential = ClientSecretCredential(
                    tenant_id=self.tenant_id,
                    client_id=self.client_id,
                    client_secret=self.client_secret
                )
                self.client = CosmosClient(self.endpoint, credential)
            except ImportError as exc:
                raise ValueError("azure-identity package required for service principal authentication. Install with: pip install azure-identity") from exc
        else:
            # Use AAD token authentication with DefaultAzureCredential
            try:
                credential = DefaultAzureCredential()
                self.client = CosmosClient(self.endpoint, credential)
            except ImportError as exc:
                raise ValueError("azure-identity package required for AAD authentication. Install with: pip install azure-identity") from exc
        
        self.database = self.client.get_database_client(self.database_name)
        self.container = self.database.get_container_client(self.container_name)
    
    def create_database_and_container(self):
        """Create the database and container if they don't exist."""
        try:
            # Create database
            self.database = self.client.create_database_if_not_exists(self.database_name)
            print(f"Database '{self.database_name}' ready")
            
            # Create container with partition key on 'category'
            partition_key = PartitionKey(path="/category")
            self.container = self.database.create_container_if_not_exists(
                id=self.container_name,
                partition_key=partition_key,
                offer_throughput=400  # Minimum throughput for shared containers
            )
            print(f"Container '{self.container_name}' ready with partition key on 'category'")
            
        except Exception as e:
            print(f"Error creating database/container: {e}")
            raise
    
    def load_products_from_json(self, file_path: str = "src/db.json") -> List[Dict[str, Any]]:
        """Load products from the JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                products = json.load(file)
            print(f"Loaded {len(products)} products from {file_path}")
            return products
        except FileNotFoundError:
            print(f"Error: File {file_path} not found")
            raise
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            raise
    
    def insert_products(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Insert products into Cosmos DB and return statistics."""
        stats: Dict[str, Any] = {
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        for product in products:
            try:
                # Insert the product document
                self.container.create_item(product)
                stats['successful'] += 1
                print(f"✓ Inserted product: {product['name']} (ID: {product['id']})")
                
            except (ValueError, TypeError, KeyError) as e:
                stats['failed'] += 1
                error_msg = f"Failed to insert {product.get('name', 'Unknown')} (ID: {product.get('id', 'Unknown')}): {str(e)}"
                stats['errors'].append(error_msg)
                print(f"✗ {error_msg}")
        
        return stats
    
    def query_products(self, query: str = "SELECT * FROM c") -> List[Dict[str, Any]]:
        """Query products from the container."""
        try:
            items = list(self.container.query_items(
                query=query,
                enable_cross_partition_query=True
            ))
            print(f"Query returned {len(items)} items")
            return items
        except (ValueError, TypeError, KeyError) as e:
            print(f"Error querying products: {e}")
            raise
    
    def get_container_stats(self) -> Dict[str, Any]:
        """Get basic statistics about the container."""
        try:
            # Get container properties
            container_props = self.container.read()
            
            # Count items
            count_query = "SELECT VALUE COUNT(1) FROM c"
            count_result = list(self.container.query_items(
                query=count_query,
                enable_cross_partition_query=True
            ))
            item_count = count_result[0] if count_result else 0
            
            return {
                'container_id': container_props['id'],
                'partition_key': container_props['partitionKey']['paths'],
                'item_count': item_count,
                'last_modified': container_props['lastModified']
            }
        except (ValueError, TypeError, KeyError) as e:
            print(f"Error getting container stats: {e}")
            return {}

def main():
    """Main function to insert products into Cosmos DB."""
    try:
        # Initialize the inserter
        inserter = CosmosDBProductInserter()
        
        # Create database and container
        inserter.create_database_and_container()
        
        # Load products from JSON file
        products = inserter.load_products_from_json()
        
        # Insert products
        print("\nInserting products into Cosmos DB...")
        stats = inserter.insert_products(products)
        
        # Print results
        print("\n=== Insertion Results ===")
        print(f"Successful: {stats['successful']}")
        print(f"Failed: {stats['failed']}")
        
        if stats['errors']:
            print("\nErrors:")
            for error in stats['errors']:
                print(f"  - {error}")
        
        # Get and display container statistics
        print("\n=== Container Statistics ===")
        container_stats = inserter.get_container_stats()
        for key, value in container_stats.items():
            print(f"{key}: {value}")
        
        # Example queries
        print("\n=== Example Queries ===")
        
        # Query all products
        all_products = inserter.query_products()
        print(f"Total products in database: {len(all_products)}")
        
        # Query by category
        electronics = inserter.query_products("SELECT * FROM c WHERE c.category = 'Electronics'")
        print(f"Electronics products: {len(electronics)}")
        
        # Query expensive products
        expensive = inserter.query_products("SELECT * FROM c WHERE c.price > 1000")
        print(f"Products over $1000: {len(expensive)}")
        
        print("\n✅ Product insertion completed successfully!")
        
    except (ValueError, TypeError, KeyError) as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 