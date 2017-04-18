#!/bin/bash
set -e

die() {
  echo "HTTP/1.1 500 Internal Server Error"
  echo "Content-Type: text/plain"
  echo
  echo "$*"
  exit 1  
}

notFound() {
  echo "HTTP/1.1 404 Not Found"
  echo "Content-Type: text/plain"
  echo
  echo "404 Not Found"
  exit 1  
}

if [ ! -d "$CA_DIR" ]; then
  die "CA not found"
fi
cd "$CA_DIR"

#1 Output
sign() {
  local paramOutput=$1
  unset cn ip ns days gp dn
  for param in ${QUERY_STRING//&/ }; do
    varname="${param%%=*}"
    varvalue="${param#*=}"
    case "$varname" in
      cn) cn=$varvalue ;;
      ip) ip=$varvalue ;;
      ns) ns=$varvalue ;;
      days) days=$varvalue ;;
      gp) gp=$varvalue ;;
      dn) dn=$varvalue ;;
    esac
  done

  [ -z "$cn" -a -z "$dn" ] && die "Either cn= or dn= is mandatory"
  [ -n "$cn" -a -n "$dn" ] && die "Pick either cn or dn"
  [ -z "$dn" ] && dn="/CN=$cn$( for i in ${gp//,/ }; do echo -n "/O=$i"; done)"
  regex=${DN_REGEX:-"^/CN=[-_:a-zA-Z0-9]+(/O=[-_:a-zA-Z0-9]+)*$"}
  [[ ! $dn =~ $regex ]] && die "The dn $dn doesn't match $regex"


  export RANDFILE=.rnd
  exec 100<ca.cnf && \
  flock 100 && \
  openssl ca \
    -batch \
    -config ca.cnf \
    -subj "$dn" \
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
