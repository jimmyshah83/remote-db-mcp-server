"""Product schema information for Cosmos DB."""
SCHEMA_INFO = '''
Cosmos DB Product Schema:
{
    "id": string,
    "name": string,
    "category": string,
    "subcategory": string,
    "brand": string,
    "description": string,
    "price": number,
    "currency": string,
    "sku": string,
    "inStock": boolean,
    "stockQuantity": number,
    "tags": [string],
    "specifications": {
        "processor": string,
        "memory": string,
        "storage": string,
        "display": string,
        "weight": string
    },
    "images": [string],
    "rating": number,
    "reviewCount": number,
    "createdAt": string,
    "updatedAt": string,
    "_rid": string,
    "_self": string,
    "_etag": string,
    "_attachments": string,
    "_ts": number
}
''' 