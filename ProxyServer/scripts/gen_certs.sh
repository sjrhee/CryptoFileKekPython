#!/bin/bash

# Default values
CN_VAL=${1:-localhost}
IP_VAL=${2:-127.0.0.1}

# Ensure we are in ProxyServer directory
cd "$(dirname "$0")/.."

echo "Generating certificates for CN=$CN_VAL and IP=$IP_VAL"
echo "Usage: ./scripts/gen_certs.sh [CommonName] [IPAddress]"

# Directory for certs
mkdir -p certs
cd certs

# 1. Generate CA Key and Cert
echo "1. Generating CA..."
openssl genrsa -out ca.key 2048
openssl req -new -x509 -days 365 -key ca.key -out ca.crt -subj "/CN=ProxyServerCA"

# 2. Generate Server Key and CSR
echo "2. Generating Server Key and CSR..."
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -subj "/CN=$CN_VAL"

# Prepare SAN extension file
echo "subjectAltName=DNS:$CN_VAL,IP:$IP_VAL" > san.ext

# 3. Sign Server Cert with CA
echo "3. Signing Server Cert..."
openssl x509 -req -days 365 -in server.csr -CA ca.crt -CAkey ca.key -set_serial 01 -out server.crt -extfile san.ext

# 4. Generate Client Key and CSR
echo "4. Generating Client Key and CSR..."
openssl genrsa -out client.key 2048
openssl req -new -key client.key -out client.csr -subj "/CN=ProxyClient"

# 5. Sign Client Cert with CA
echo "5. Signing Client Cert..."
openssl x509 -req -days 365 -in client.csr -CA ca.crt -CAkey ca.key -set_serial 02 -out client.crt

# Clean up
rm san.ext

echo "----------------------------------------"
echo "Certificates generated in $(pwd)/"
echo "Common Name (CN): $CN_VAL"
echo "Subject Alt Name (SAN): DNS:$CN_VAL, IP:$IP_VAL"
echo "----------------------------------------"
