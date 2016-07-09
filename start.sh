#!/bin/sh
set -e

info() {
    echo "[$(date -u '+%Y/%m/%d %H:%M:%S GMT')] $*"
}

mkdir -p "${CERT_TLS%/*}" "$CA_DIR"

cd /tmp
if [ ! -f "$CERT_TLS" ]; then
    info "$CERT_TLS not found, building a new auto signed certificate"
    trap "rm -f /tmp/crt.pem /tmp/key.pem" EXIT
    openssl req -x509 -newkey rsa:2048 -keyout key.pem -out crt.pem -days 3652 -nodes -subj '/CN=localhost'
    cat crt.pem key.pem > "$CERT_TLS"
    chmod 400 "$CERT_TLS"
    info "New cert successfully built"
else
    info "Found TLS cert: $CERT_TLS"
fi

cd "$CA_DIR"
if [ ! -f ca.pem ] || [ ! -f ca-key.pem ]; then
    info "CA cert or private key not found, building..."
    openssl genrsa -out ca-key.pem 2048
    openssl req -x509 -new -nodes -key ca-key.pem -days 3652 -out ca.pem -subj "/CN=$CA_CN"
    chmod 400 ca.pem ca-key.pem
    info "CA successfully built"
else
    info "Found CA cert and private key: $CA_DIR"
fi

if [ ! -f serial.txt ]; then
    echo -n "0001" > serial.txt
fi

exec lighttpd -f /etc/lighttpd/lighttpd.conf -D
