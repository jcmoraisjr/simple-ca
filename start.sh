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

if [ ! -f ca.cnf ]; then
    cp /srv/ca.cnf .
fi

mkdir -p private newcerts
chmod 700 private
touch index.txt

# 0.1 to 0.2 migrations
if [ -f ca-key.pem ] && [ ! -f private/ca-key.pem ]; then
    mv ca-key.pem private/ca-key.pem
fi
if [ -f serial.txt ] && [ ! -f serial ]; then
    mv serial.txt serial
fi

if [ ! -f ca.pem ] || [ ! -f private/ca-key.pem ]; then
    info "CA cert or private key not found, building..."
    openssl genrsa -out private/ca-key.pem 2048
    openssl req \
      -x509 -new -nodes -days 3652 -subj "/CN=$CA_CN" \
      -key private/ca-key.pem -out ca.pem
    info "CA successfully built"
else
    info "Found CA cert and private key: $CA_DIR"
fi
chmod 400 private/ca-key.pem

if [ ! -f serial ]; then
    echo -n "0001" > serial
fi

cd /
exec lighttpd -f /etc/lighttpd/lighttpd.conf -D
