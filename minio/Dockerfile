FROM minio/minio:latest

ENV MINIO_ROOT_USER=minioadmin
ENV MINIO_ROOT_PASSWORD=minioadmin

RUN mkdir -p /data

EXPOSE 9000
EXPOSE 9001

ENTRYPOINT ["minio", "server", "/data", "--console-address", ":9001"]