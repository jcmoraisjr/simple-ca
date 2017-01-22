#!/bin/bash
set -e

info() {
    echo "[$(date -u '+%Y/%m/%d %H:%M:%S GMT')] $*"
}

mkdir -p "${CERT_TLS%/*}" "$CA_DIR"

cd "$CA_DIR"

if [ ! -f ca.cnf ]; then
    sed "s/{{CRT_DAYS}}/${CRT_DAYS:-365}/" /srv/ca.cnf > ca.cnf
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
        -x509 -new -nodes -days ${CA_DAYS:-3652} -subj "/CN=$CA_CN" \
        -key private/ca-key.pem -out ca.pem
    info "CA successfully built"
else
    info "Found CA cert and private key: $CA_DIR"
fi
chmod 400 private/ca-key.pem

if [ ! -f serial ]; then
    echo -n "0001" > serial
fi

if [ ! -f "$CERT_TLS" ]; then
    info "$CERT_TLS not found, building new private key and certificate"
    trap "rm -f /tmp/key.pem /tmp/crt.pem" EXIT
    openssl req -new -newkey rsa:2048 -nodes -keyout /tmp/key.pem -subj "/" | openssl ca \
        -batch \
        -config ca.cnf \
        -subj "/CN=${CERT_TLS_DNS:-$(hostname)}" \
        -notext \
        -days "${CERT_TLS_DAYS:-365}" \
        -in <(cat -) \
        -out /tmp/crt.pem \
        -extfile <(
            echo "basicConstraints = CA:FALSE"
            echo "keyUsage = nonRepudiation, digitalSignature, keyEncipherment"
            echo "extendedKeyUsage = clientAuth, serverAuth"
            if [ -n "${CERT_TLS_DNS}" ] || [ -n "$CERT_TLS_IP" ]; then
                echo "subjectAltName = @alt_names"
                echo "[ alt_names ]"
                [ -n "$CERT_TLS_DNS" ] && echo "DNS.1 = $CERT_TLS_DNS"
                [ -n "$CERT_TLS_IP" ] && echo "IP.1 = $CERT_TLS_IP"
            fi
        )
    cat /tmp/crt.pem /tmp/key.pem > "$CERT_TLS"
    rm -f /tmp/*.pem
    chmod 400 "$CERT_TLS"
    if [ -z "${CERT_TLS_DNS}" ] && [ -z "$CERT_TLS_IP" ]; then
        info "Define CERT_TLS_DNS or CERT_TLS_IP (or both) to create a valid tls cert"
    fi
    info "New cert successfully built"
else
    info "Found TLS cert: $CERT_TLS"
fi

exec lighttpd -f /etc/lighttpd/lighttpd.conf -D
