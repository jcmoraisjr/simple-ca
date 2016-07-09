TAG=quay.io/jcmoraisjr/simple-ca:latest
build:
	docker build --tag=$(TAG) .
run:
	docker stop ca && docker rm ca || :
	docker run -d --name ca -p 80:8080 -p 443:8443 $(TAG)
