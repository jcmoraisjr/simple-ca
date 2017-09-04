#!/bin/bash
set -e

info() {
    echo "[$(date -u '+%Y/%m/%d %H:%M:%S GMT')] $*"
}

CA_LIST="${CA_LIST:-default}"
if ! grep -Eq '^([a-z0-9_]+,)*[a-z0-9_]+$' <<<"$CA_LIST"; then
    echo "Authority IDs must match [a-z0-9_]"
    exit 1
fi

mkdir -p "${CERT_TLS%/*}" "$CA_DIR"
cd "$CA_DIR"

# 0.7 to 0.8 migration
if [ -f ca.cnf ] && [ ! -d default ]; then
    echo "Moving to multi authority schema"
    mkdir _d
    mv .rnd [a-z]* _d || :
    mv _d default
fi

for ca_id in ${CA_LIST//,/ }; do
    mkdir -p "$ca_id"
    cd "$ca_id"

    CRT_DAYS_name="CRT_DAYS_$ca_id"
    CRT_DAYS_value="${!CRT_DAYS_name:-$CRT_DAYS}"

    CA_DAYS_name="CA_DAYS_$ca_id"
    CA_DAYS_value="${!CA_DAYS_name:-$CA_DAYS}"

    CA_CN_name="CA_CN_$ca_id"
    CA_CN_value="${!CA_CN_name:-$CA_CN}"

    if [ ! -f ca.cnf ]; then
        sed "s/{{CRT_DAYS}}/${CRT_DAYS_value:-365}/" /srv/ca.cnf > ca.cnf
    fi

    mkdir -p private newcerts
    chmod 700 private
    touch index.txt

    if [ ! -f ca.pem ] || [ ! -f private/ca-key.pem ]; then
        info "CA cert or private key not found, building CA \"$ca_id\"..."
        openssl genrsa -out private/ca-key.pem 2048
        openssl req \
            -x509 -new -nodes -days ${CA_DAYS_value:-3652} -subj "/CN=$CA_CN_value" \
            -key private/ca-key.pem -out ca.pem
        info "CA successfully built"
    else
        info "Found CA cert and private key: $PWD"
    fi
    chmod 400 private/ca-key.pem

    if [ ! -f serial ]; then
        echo -n "0001" > serial
    fi
    cd ..
done

cd "${CA_LIST%%,*}"
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
cd ..

exec lighttpd -f /etc/lighttpd/lighttpd.conf -D
