FROM alpine:3.6
RUN apk upgrade --no-cache && apk add --no-cache bash openssl lighttpd

ENV CERT_TLS=/ssl/www/localhost.pem
ENV CA_LIST=default
ENV CA_DEFAULT=default
ENV CA_DIR=/ssl/ca
ENV CA_CN=my-ca
ENV TOKEN=
 
RUN cd /etc/lighttpd/\
 && mv lighttpd.conf lighttpd.conf.orig\
 && mv mod_cgi.conf mod_cgi.conf.orig

COPY lighttpd/ /etc/lighttpd/
COPY index.cgi /var/www/localhost/htdocs/
COPY ca.cnf /srv/
COPY start.sh /

RUN chmod +x /start.sh /var/www/localhost/htdocs/index.cgi\
 && mkdir -p /ssl\
 && chown lighttpd:lighttpd /run /ssl /var/www/localhost/htdocs

WORKDIR /var/www/localhost/htdocs
USER lighttpd
CMD ["/start.sh"]
