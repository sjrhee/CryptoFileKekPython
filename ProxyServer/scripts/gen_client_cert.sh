#!/bin/bash

# Default values
CLIENT_NAME=${1:-ProxyClient}
OUTPUT_NAME=${2:-client}

# Ensure we are in ProxyServer directory
cd "$(dirname "$0")/.."

echo "Generating Client Certificate"
echo "CN: $CLIENT_NAME"
echo "Output Files: certs/$OUTPUT_NAME.crt, certs/$OUTPUT_NAME.key"
echo "Usage: ./scripts/gen_client_cert.sh [CommonName] [OutputFilenameBase]"

# Check if CA exists
if [ ! -f "certs/ca.crt" ] || [ ! -f "certs/ca.key" ]; then
    echo "Error: CA certificate or key not found in certs/. Run gen_certs.sh first."
    exit 1
fi

cd certs

# 1. Generate Client Key and CSR
echo "1. Generating Client Key and CSR..."
openssl genrsa -out "${OUTPUT_NAME}.key" 2048
openssl req -new -key "${OUTPUT_NAME}.key" -out "${OUTPUT_NAME}.csr" -subj "/CN=$CLIENT_NAME"

# 2. Sign Client Cert with existing CA
echo "2. Signing Client Cert..."
# Serial number management is tricky in simple scripts, we'll just use a random one or generic one. 
# For simplicity in this dev tool, we'll use date-based serial or just letting openssl handle it if configured, 
# but here we manually set it. To allow multiple, we ideally need a serial file. 
# We will just use a random 8-digit serial to minimize collision risk in dev.
SERIAL=$(openssl rand -hex 4)
openssl x509 -req -days 365 -in "${OUTPUT_NAME}.csr" -CA ca.crt -CAkey ca.key -set_serial "0x$SERIAL" -out "${OUTPUT_NAME}.crt"

# Clean up CSR
rm "${OUTPUT_NAME}.csr"

echo "----------------------------------------"
echo "Client Certificate generated:"
echo " - Key: $(pwd)/${OUTPUT_NAME}.key"
echo " - Cert: $(pwd)/${OUTPUT_NAME}.crt"
echo "----------------------------------------"
