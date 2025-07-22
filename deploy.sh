ENV_ARGS=$(grep -v '^#' .env | paste -sd' ' -)
az containerapp create \
  --name cosmossearchmcp-aca \
  --resource-group rg-js-mcp-demo-01 \
  --environment mcpdemo-aca-env \
  --image jsmcpdemo.azurecr.io/cosmossearchmcp:latest \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 1 \
  --env-vars "$ENV_ARGS" \
  --registry-server jsmcpdemo.azurecr.io
