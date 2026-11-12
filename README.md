# Repeater DNS directory

This service lets clients find a registered repeater node through DNS. It reads
registration updates from Kafka and answers A, TXT, and IAX SRV queries for the node
domain you configure. Only IPv4 registrations are supported.

You need Docker, a reachable Kafka broker, and a registrar publishing to the same
Kafka topic. Each DNS instance reads the full topic and keeps its own directory in
memory. After a restart, it rebuilds that directory from Kafka and ignores expired
registrations.

Full deployment and configuration details are in the [Register-DNS_Server operator guide](https://hamlink-canada.github.io/apt-rpt-docs/projects/dns/).

## Run the service

Choose a versioned image from `ghcr.io/hamlink-canada/register-dns_server` when a release
is available. To run this checkout before an image is published, follow
[Build an image](#build-an-image) and use `rpt-dnsserver:local` below.

Replace the broker address and node domain with your own:

```sh
IMAGE=rpt-dnsserver:local

docker run -d --name rpt-dns --restart unless-stopped \
  --publish 5054:5054/udp \
  --publish 5054:5054/tcp \
  --env RPT_KAFKA__BOOTSTRAP=kafka.example.org:9092 \
  --env RPT_KAFKA__TOPIC=rpt.registrations \
  --env RPT_DOMAIN=nodes.example.org \
  "$IMAGE"
```

The Kafka topic must contain compatible registration messages. The broker addresses
advertised by Kafka must also be reachable from the container.

The example listens on host port 5054 so you can try it without replacing an existing
DNS server. To serve standard DNS traffic, publish host port 53 to container port
5054 for both UDP and TCP. Configure your resolver to send queries for the chosen
node domain to this service.

## Configuration

The settings most deployments need are:

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `RPT_DOMAIN` | `nodes.example.org` | Domain used in node lookups. |
| `RPT_KAFKA__BOOTSTRAP` | `localhost:9092` | Kafka bootstrap address. |
| `RPT_KAFKA__TOPIC` | `rpt.registrations` | Topic used by the registrars. |
| `RPT_PORT` | `5054` | TCP and UDP port inside the container. |
| `RPT_CACHE_SIZE` | `10000` | Maximum number of directory entries. |
| `RPT_WORKERS` | `32` | Maximum concurrent request workers per listener. |

Dynaconf loads `settings.toml`, then an optional `.secrets.toml`, from the working
directory. Environment variables beginning with `RPT_` override those files. Use
two underscores for nested settings, as in `RPT_KAFKA__TOPIC`.

To keep configuration on the host, mount a directory at `/config` and set
`RPT_CONFIG_DIR=/config`. Files use plain TOML without environment sections. Keep
credentials out of version control. See [directory behavior](docs/directory.md)
for the remaining settings and Kafka replay details.

## Check a registration

For a node that has registered as `1234`:

```sh
dig @127.0.0.1 -p 5054 1234.nodes.example.org A
dig @127.0.0.1 -p 5054 1234.nodes.example.org TXT
dig @127.0.0.1 -p 5054 _iax._udp.1234.nodes.example.org SRV
```

The A record contains the node's address, TXT contains registration metadata, and
SRV contains its IAX endpoint. Answers have a TTL of at most 60 seconds, shortened
when the registration is about to expire. Replaying an old Kafka message does not
extend its lifetime.

If a lookup returns `SERVFAIL`, check that the node has a current registration and
that the query uses the configured domain. Missing or expired nodes and unsupported
query types receive `SERVFAIL`.

```sh
docker logs --tail 100 rpt-dns
docker stop rpt-dns
```

If no registrations appear, check the broker's advertised addresses, the topic name,
and whether a registrar has published an update. Size the directory for the number
of nodes on your network. No persistent volume is required for the in-memory cache;
Kafka retention determines what can be replayed after a restart.

## Build an image

From this checkout, with Docker Buildx and Python 3.13+ installed:

```sh
PROTOBUF_REV=$(python3 scripts/dependency.py)
docker buildx build --load \
  --build-context "rpt_protobuf=https://github.com/Hamlink-Canada/rpt_protobuf.git#${PROTOBUF_REV}" \
  --tag rpt-dnsserver:local .
```

This fetches the public protobuf dependency from its `main` branch.
The image runs as UID/GID 10001 and starts `rpt-dns`. Configuration files mounted into
the container must be readable by that user.

## Development

Use Python 3.13+ and uv. Place `Register-DNS_Server` and `rpt_protobuf` next to one another,
with the library checked out on an up-to-date `main` branch.
The uv source override installs that sibling library in editable mode.

```sh
uv sync --locked
make check test build
uv run --locked rpt-dns
```

To build with local library changes, replace the remote build context above with
`--build-context rpt_protobuf=../rpt_protobuf`. Standard Python installations use the
`main` branch declared in `pyproject.toml`. Refresh the sibling checkout and
lockfile when dependency metadata changes; generated bindings belong in
`rpt_protobuf`.

CI checks Python 3.13 and 3.14 and is configured to build and check runtime imports
on Linux AMD64 and ARM64. Published GitHub releases with `vMAJOR.MINOR.PATCH` tags publish versioned images
and commit-SHA tags;
stable releases also update `latest`. Pull requests do not publish images. Python
packages are not published to PyPI.

Images are published only after the release workflow passes its tests and container
checks. Publishing a GitHub prerelease (for example, `v1.0.1-rc.1`) publishes its
version and commit-SHA image tags without updating `latest`. Pushing a tag alone
does not publish an image. Registry authentication uses the built-in `GITHUB_TOKEN`.

## License

[AGPL-3.0-or-later](LICENSE).
