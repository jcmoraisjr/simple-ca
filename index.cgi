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
  unset cn ip ns
  for param in ${QUERY_STRING//&/ }; do
    varname="${param%%=*}"
    varvalue="${param#*=}"
    case "$varname" in
      cn) cn=$varvalue ;;
      ip) ip=$varvalue ;;
      ns) ns=$varvalue ;;
    esac
  done

  [ -z "$cn" ] && die "cn= is mandatory"

  exec 100<ca.cnf && \
  flock 100 && \
  openssl ca \
    -batch \
    -config ca.cnf \
    -subj "/CN=$cn" \
    -notext \
    -in <(cat -) \
    -out "$paramOutput" \
    -extfile <(
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
