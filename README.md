# Simple-CA

A very simple automated Certificate Authority. Such CA is useful on auto provisioned clusters secured by client certificates, like [etcd](https://coreos.com/etcd/) and [Kubernetes](http://kubernetes.io/).

[![Docker Repository on Quay](https://quay.io/repository/jcmoraisjr/simple-ca/status "Docker Repository on Quay")](https://quay.io/repository/jcmoraisjr/simple-ca)

# Usage

Run the CA:

    docker run -d -p 80:8080 -p 443:8443 quay.io/jcmoraisjr/simple-ca

Create a private key and certificate request:

    openssl genrsa -out host-key.pem 2048
    openssl req -new -key host-key.pem -out host.csr -subj "/"

Sign the certificate -- change `localhost` to the IP if Docker Server is on a VM - eg Docker Machine:

    curl --insecure -XPOST -d"$(<host.csr)" -o host.pem "https://localhost/sign?cn=my-host"

Since 0.2 the `cn` parameter is mandatory.

Check the certificate:

    openssl x509 -noout -text -in host.pem

Using alternative IP, NS or both:

    curl --insecure -XPOST -d"$(<host.csr)" -o host.pem "https://localhost/sign?cn=my-host&ip=10.0.0.1"
    curl --insecure -XPOST -d"$(<host.csr)" -o host.pem "https://localhost/sign?cn=my-host&ip=10.0.0.1,192.168.0.1"
    curl --insecure -XPOST -d"$(<host.csr)" -o host.pem "https://localhost/sign?cn=my-host&ns=localhost,my-host.localdomain"
    curl --insecure -XPOST -d"$(<host.csr)" -o host.pem "https://localhost/sign?cn=my-host&ip=10.0.0.1&ns=my-host.localdomain"

Using alternative number of days:

    curl --insecure -XPOST -d"$(<host.csr)" -o host.pem "https://localhost/sign?cn=my-host&days=30"

# Options

The following environment variables may be defined:

* `CRT_DAYS`: default number of days to certify signed certificates, defaults to 365, can be changed per signed certificate
* `CA_DAYS`: number of days to certify the CA certificate, defaults to 3652 (10 years).

# Deploy

* Mount the `/ssl` directory to ensure that nothing will be lost if the container is recreated
* The external directory should be owned by container's `lighttpd` user (uid 100)
* Point `CERT_TLS` env var to the certificate and key used by the web server, otherwise a self signed certificate will be used
* Point `CA_DIR` to the directory with your own `ca.pem` and `ca-key.pem`, otherwise a new cert and key will be generated
* A self generated CA will use `CA_CN` as its common name

This systemd unit has the most common configuration:

    [Unit]
    Description=Simple CA
    After=docker.service
    Requires=docker.service
    [Service]
    ExecStartPre=-/usr/bin/docker stop simple-ca
    ExecStartPre=-/usr/bin/docker rm simple-ca
    ExecStartPre=/usr/bin/mkdir -p /var/lib/simple-ca/ssl
    ExecStartPre=/bin/bash -c 'chown $(docker run --rm quay.io/jcmoraisjr/simple-ca id -u lighttpd) /var/lib/simple-ca/ssl'
    ExecStart=/usr/bin/docker run \
      --name simple-ca \
      -p 80:8080 \
      -p 443:8443 \
      -e CERT_TLS=/ssl/www/caserver.pem \
      -e CA_CN=mycompany-ca \
      -v /var/lib/simple-ca/ssl:/ssl \
      quay.io/jcmoraisjr/simple-ca:latest
    RestartSec=10s
    Restart=always
    [Install]
    WantedBy=multi-user.target
