There are 2 big files with size > 100mb (look at .gitignore). So sorry...  
But both files will be automatically downloaded when installing stanza.

run this line on terminal to download en_core_web_sm:
python -m spacy download en_core_web_sm

how to use qdrant api:
python:

```
from qdrant_client import QdrantClient

qdrant_client = QdrantClient(
    url="https://88b6a5d8-fc19-4e30-a70c-6a3b1606c231.eu-west-1-0.aws.cloud.qdrant.io:6333",
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.iXGhzVC772fhrgZ1l7s-cJydhNvnCgy6Vngd8fQmZWo",
)

print(qdrant_client.get_collections())
```

curl:

```
curl \
    -X GET 'https://88b6a5d8-fc19-4e30-a70c-6a3b1606c231.eu-west-1-0.aws.cloud.qdrant.io:6333' \
    --header 'api-key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.iXGhzVC772fhrgZ1l7s-cJydhNvnCgy6Vngd8fQmZWo'
```
