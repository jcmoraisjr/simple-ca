# Simple-CA

A very simple automated Certificate Authority. Such CA is useful on auto provisioned clusters secured by client certificates, like [etcd](https://coreos.com/etcd/) and [Kubernetes](http://kubernetes.io/).

[![Docker Repository on Quay](https://quay.io/repository/jcmoraisjr/simple-ca/status "Docker Repository on Quay")](https://quay.io/repository/jcmoraisjr/simple-ca)

# Usage

Run the CA:

    docker run -d -p 80:8080 -p 443:8443 quay.io/jcmoraisjr/simple-ca

Create a private key and certificate request:

    openssl req -new -newkey rsa:2048 -keyout host-key.pem -nodes -out host.csr -subj "/"

Sign the certificate -- change `localhost` to the IP if Docker Server is on a VM - eg Docker Machine:

    curl -fk --data-binary @host.csr -o host.pem "https://localhost/sign?cn=my-host&ns=my-host.localdomain"

Check the certificate:

    openssl x509 -noout -text -in host.pem

Using `dn` instead `cn`:

    curl -fk --data-binary @host.csr -o host.pem "https://localhost/sign?dn=/CN=my-host&ns=my-host.localdomain"

Shortcut to organizationName and `dn` syntax - Note that `ca.cnf` changed on `0.7`,
you should update or remove `<local-ca-dir>/ssl/ca/ca.cnf` before restart `simple-ca`:

    curl -fk --data-binary @host.csr -o host.pem "https://localhost/sign?cn=my-host&o=company&ns=my-host.localdomain"
    curl -fk --data-binary @host.csr -o host.pem "https://localhost/sign?dn=/CN=my-host/O=company&ns=my-host.localdomain"

One liner key and cert:

    openssl req -new -newkey rsa:2048 -keyout host-key.pem -nodes -subj "/" | \
      curl -fk --data-binary @- -o host.pem "https://localhost/sign?cn=my-host&ns=my-host.localdomain"

Using subject from the request - `cn` is optional since `0.7`:

    openssl req -new -newkey rsa:2048 -keyout host-key.pem -nodes -subj "/CN=my-host" | \
      curl -fk --data-binary @- -o host.pem "https://localhost/sign?ns=my-host.localdomain"

Using alternative IP, NS or both:

**Note:** If neither IP nor NS is provided, a client certificate would be generated. Always provide IP, NS or both for server certificates.

    curl -fk --data-binary @host.csr -o host.pem "https://localhost/sign?cn=my-host&ip=10.0.0.1"
    curl -fk --data-binary @host.csr -o host.pem "https://localhost/sign?cn=my-host&ip=10.0.0.1,192.168.0.1"
    curl -fk --data-binary @host.csr -o host.pem "https://localhost/sign?cn=my-host&ns=localhost,my-host.localdomain"
    curl -fk --data-binary @host.csr -o host.pem "https://localhost/sign?cn=my-host&ip=10.0.0.1&ns=my-host.localdomain"

Using alternative number of days:

    curl -fk --data-binary @host.csr -o host.pem "https://localhost/sign?cn=my-host&days=30"

# Options

The following optional environment variables may be defined:

* `CRT_DAYS`: default number of days to certify signed certificates, defaults to 365, can be changed per signed certificate
* `CA_DAYS`: number of days to certify the CA certificate, defaults to 3652 (10 years)
* `CA_DIR`: path to `ca.pem` and `private/ca-key.pem` used to sign certificates, defaults to `/ssl/ca`. A new cert and key will be created if not found
* `CA_CN`: Aa self generated CA will use `CA_CN` as its common name, defaults to `my-ca`
* `CERT_TLS`: TLS certificate and key file used by web server to provide https, defaults to `/ssl/www/localhost.pem`. If not found, CA itself will sign a certificate
* `CERT_TLS_DNS`: name server of the CA server, used on auto generated TLS certificate. At least one of `CERT_TLS_DNS` or `CERT_TLS_IP` should be provided
* `CERT_TLS_IP`: public IP of the CA server, used on auto generated TLS certificate. At least one of `CERT_TLS_DNS` or `CERT_TLS_IP` should be provided
* `CERT_TLS_DAYS`: number of days to certify the CA server cert, used on auto generated TLS certificate, defaults to 365 days

# Deploy

* Mount the `/ssl` directory to ensure that nothing will be lost if the container is recreated
* The external directory should be owned by container's `lighttpd` user (uid 100)

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
      -e CERT_TLS_DNS=ca.mycompany.com \
      -e CA_CN=MyCompany-CA \
      -v /var/lib/simple-ca/ssl:/ssl \
      quay.io/jcmoraisjr/simple-ca:latest
    RestartSec=10s
    Restart=always
    [Install]
    WantedBy=multi-user.target
