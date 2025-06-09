#!/bin/bash

# SSL CERTIFICATE FIX FOR BOLTZ-2 ON CHEAHA CLUSTER
# This script resolves the SSL certificate verification error

echo "🔧 FIXING SSL CERTIFICATE ISSUE FOR BOLTZ-2..."

# Method 1: Use system certificates
export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
export CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# Method 2: If system certs don't exist, try alternative paths
if [ ! -f "$SSL_CERT_FILE" ]; then
    export SSL_CERT_FILE=/etc/pki/tls/certs/ca-bundle.crt
    export REQUESTS_CA_BUNDLE=/etc/pki/tls/certs/ca-bundle.crt
    export CURL_CA_BUNDLE=/etc/pki/tls/certs/ca-bundle.crt
fi

# Method 3: Download certificates if needed
if [ ! -f "$SSL_CERT_FILE" ]; then
    echo "📥 Downloading certificate bundle..."
    mkdir -p ~/.local/share/ca-certificates
    wget --no-check-certificate -O ~/.local/share/ca-certificates/cacert.pem https://curl.se/ca/cacert.pem
    export SSL_CERT_FILE=~/.local/share/ca-certificates/cacert.pem
    export REQUESTS_CA_BUNDLE=~/.local/share/ca-certificates/cacert.pem
    export CURL_CA_BUNDLE=~/.local/share/ca-certificates/cacert.pem
fi

# Method 4: Python-specific SSL configuration
export PYTHONHTTPSVERIFY=1
export PYTHONSSLTESTMODE=1

# Test the fix
echo "🧪 Testing SSL configuration..."
python3 -c "
import ssl
import urllib.request
try:
    context = ssl.create_default_context()
    print('✅ SSL context created successfully')
    print(f'Certificate file: {ssl.get_default_verify_paths().cafile}')
except Exception as e:
    print(f'❌ SSL error: {e}')
"

echo "📝 SSL environment variables set:"
echo "SSL_CERT_FILE=$SSL_CERT_FILE"
echo "REQUESTS_CA_BUNDLE=$REQUESTS_CA_BUNDLE"

echo "🚀 Ready to run Boltz-2!"
echo "Usage: source ssl_fix_boltz.sh && boltz predict [your_yaml_file]" 