#!/bin/bash
set -e

d() {
  date -u '+%Y/%m/%d %H:%M:%S GMT'
}

die() {
  echo "HTTP/1.1 400 Bad Request"
  echo "Content-Type: text/plain"
  echo
  echo "$*"
  echo "$*" | sed "s;^;[$(d)] ERROR - ;" >&2
  exit 1  
}

notFound() {
  echo "HTTP/1.1 404 Not Found"
  echo "Content-Type: text/plain"
  echo
  echo "404 Not Found"
  exit 1  
}

info() {
  echo "[$(d)] $*" >&2
}

if [ ! -d "$CA_DIR" ]; then
  die "CA not found"
fi
cd "$CA_DIR"

#1 Output
sign() {
  local paramOutput=$1
  unset dn cn ip ns o days
  # No decode, no space from QUERY_STRING
  for param in ${QUERY_STRING//&/ }; do
    varname="${param%%=*}"
    varvalue="${param#*=}"
    case "$varname" in
      dn) dn=$varvalue ;;
      cn) cn=$varvalue ;;
      ip) ip=$varvalue ;;
      ns) ns=$varvalue ;;
      o) o=$varvalue ;;
      days) days=$varvalue ;;
    esac
  done

  [ -n "$cn" -a -n "$dn" ] && die "Pick either cn or dn"
  [ -z "$dn" -a -n "$cn" ] && dn="/CN=$cn"
  for vo in ${o//,/ }; do
    dn+="/O=$vo"
  done

  export RANDFILE=.rnd
  exec 100<ca.cnf && \
  flock 100 && \
  openssl ca \
    -batch \
    -config ca.cnf \
    $([ -n "$dn" ] && echo "-subj $dn" || :) \
    -notext \
    $([ -n "$days" ] && echo "-days $days" || :) \
    -in <(cat -) \
    -out "$paramOutput" \
    -extfile <(
      echo "basicConstraints = CA:FALSE"
      echo "keyUsage = nonRepudiation, digitalSignature, keyEncipherment"
      echo "extendedKeyUsage = clientAuth$([ -n "$ip$ns" ] && echo ", serverAuth")"
      if [ -n "$ip" ] || [ -n "$ns" ]; then
        echo "subjectAltName = @alt_names"
        echo "[ alt_names ]"
        i=1
        for alt_ip in ${ip//,/ }; do
          echo "IP.${i} = $alt_ip"
          ((i++))
        done
        i=1
        for alt_ns in ${ns//,/ }; do
          echo "DNS.${i} = $alt_ns"
          ((i++))
        done
      fi
    )
}

case "$PATH_INFO" in
  /sign)
    CRT=/tmp/crt-$$.pem
    trap "rm -f $CRT" EXIT
    err=$(sign "$CRT" 2>&1) || die "$err"
    info "New cert: $(openssl x509 -noout -subject -in $CRT)"
    out=$CRT
    ;;
  /ca)
    out=ca.pem
    ;;
  *)
    notFound
    ;;
esac

echo "HTTP/1.1 200 OK"
echo "Content-Type: text/plain"
echo
cat "$out"
