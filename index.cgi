#!/bin/bash
set -e

d() {
  date -u '+%Y/%m/%d %H:%M:%S GMT'
}

badRequest() {
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

#1 token
checktoken() {
  IFS=":" read -r algo hash <<<"$TOKEN"
  [ -z "$hash" ] && echo "Hash algorithm wasn't provided" && return 1
  case "$algo" in
    md5|sha1|sha256|sha512) check=$(echo -n "$1" | openssl dgst -$algo -r | cut -d' ' -f1) ;;
    *) echo "Unsupported algorithm: $algo" && return 1 ;;
  esac
  [ "$check" != "$hash" ] && echo "Invalid token" && return 1
  return 0
}

### sign() exec as a subprocess - do not write HTTP headers
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
      token) token=$varvalue ;;
    esac
  done

  [ -n "$TOKEN" ] && ! checktoken "$token" && return 1
  [ -n "$cn" -a -n "$dn" ] && echo "Pick either cn or dn" && return 1

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

# breakdown /<ca_method>[/<ca_id>]
IFS="/" read -r ca_method ca_id <<<"${PATH_INFO#/}"
ca_id="${ca_id:-$CA_DEFAULT}"
grep -Eq ",${ca_id}," <<<",${CA_LIST}," || notFound
cd "$CA_DIR/$ca_id" 2>/dev/null || notFound
case "$ca_method" in
  sign)
    CRT=/tmp/crt-$$.pem
    trap "rm -f $CRT" EXIT
    err=$(sign "$CRT" 2>&1) || badRequest "$err"
    info "New cert: $(openssl x509 -noout -subject -in $CRT)"
    out=$CRT
    ;;
  ca)
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
