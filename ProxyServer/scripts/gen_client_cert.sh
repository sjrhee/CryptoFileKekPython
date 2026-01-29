#!/bin/bash

# Default values
CLIENT_NAME=${1:-ProxyClient}
OUTPUT_NAME=${2:-client}
CLIENT_IP=$3

# Ensure we are in ProxyServer directory
cd "$(dirname "$0")/.."

echo "Generating Client Certificate"
echo "CN: $CLIENT_NAME"
if [ -n "$CLIENT_IP" ]; then
    echo "IP: $CLIENT_IP"
fi
echo "Output Files: certs/$OUTPUT_NAME.crt, certs/$OUTPUT_NAME.key"
echo "Usage: ./scripts/gen_client_cert.sh [CommonName] [OutputFilenameBase] [OptionalIP]"

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

# 2. Prepare SAN extension if IP is provided
EXT_OPT=""
if [ -n "$CLIENT_IP" ]; then
    echo "Adding subjectAltName=IP:$CLIENT_IP"
    echo "subjectAltName=IP:$CLIENT_IP" > "${OUTPUT_NAME}.ext"
    EXT_OPT="-extfile ${OUTPUT_NAME}.ext"
fi

# 3. Sign Client Cert with existing CA
echo "2. Signing Client Cert..."
SERIAL=$(openssl rand -hex 4)
openssl x509 -req -days 365 -in "${OUTPUT_NAME}.csr" -CA ca.crt -CAkey ca.key -set_serial "0x$SERIAL" -out "${OUTPUT_NAME}.crt" $EXT_OPT

# Clean up
rm "${OUTPUT_NAME}.csr"
[ -f "${OUTPUT_NAME}.ext" ] && rm "${OUTPUT_NAME}.ext"

echo "----------------------------------------"
echo "Client Certificate generated:"
echo " - Key: $(pwd)/${OUTPUT_NAME}.key"
echo " - Cert: $(pwd)/${OUTPUT_NAME}.crt"
if [ -n "$CLIENT_IP" ]; then
    echo " - SAN: IP:$CLIENT_IP"
fi
echo "----------------------------------------"
