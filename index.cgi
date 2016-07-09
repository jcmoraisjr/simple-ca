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
  for param in ${QUERY_STRING//&/ }; do
    varname="${param%%=*}"
    varvalue="${param#*=}"
    case "$varname" in
      ip) ip=$varvalue ;;
      ns) ns=$varvalue ;;
    esac
  done

  # TODO concurrency on serial.txt 
  openssl x509 \
    -req \
    -sha256 \
    -in <(cat -) \
    -CA ca.pem \
    -CAkey ca-key.pem \
    -set_serial 0x$(<serial.txt) \
    -out "$paramOutput" \
    -days 1826 \
    -extfile <(
      if [ -n "$ip" ] || [ -n "$ns" ]; then
        echo "subjectAltName = @alt_names"
        echo "[alt_names]"
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
    ) &&\
  printf '%04X' $((0x$(<serial.txt)+1)) > serial.txt.$$ &&\
  mv -f serial.txt.$$ serial.txt
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
